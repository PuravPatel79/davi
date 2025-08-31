import boto3
import os
import uuid
import json
import time

class SandboxExecutorAWS:
    """
    Manages the lifecycle of secure, single-use AWS Fargate tasks for executing user code.
    """
    def __init__(self):
        self.ecs_client = boto3.client('ecs', region_name=os.getenv("AWS_REGION", "us-east-2"))
        self.s3_client = boto3.client('s3', region_name=os.getenv("AWS_REGION", "us-east-2"))
        
        self.cluster_name = os.getenv("ECS_CLUSTER_NAME")
        self.sandbox_task_definition = os.getenv("SANDBOX_TASK_DEFINITION_ARN")
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        self.subnet_ids = os.getenv("SUBNET_IDS", "").split(',')
        self.security_group_ids = os.getenv("SECURITY_GROUP_IDS", "").split(',')

    def execute_code(self, session_id, code: str, data_s3_key: str):
        """
        Launches a Fargate task to execute code. This is a fire-and-forget operation.
        The task will read data and code from S3, execute, and write the result back to S3.
        """
        if not all([self.cluster_name, self.sandbox_task_definition, self.s3_bucket_name, self.subnet_ids, self.security_group_ids]):
            print("Error: Missing required AWS configuration for SandboxExecutor.")
            return {"error": "Server is not configured for AWS execution."}

        execution_id = str(uuid.uuid4())
        code_s3_key = f"code/{session_id}/{execution_id}.py"
        result_s3_key = f"results/{session_id}/{execution_id}.json"

        try:
            # 1. Upload the user's code to S3
            self.s3_client.put_object(Bucket=self.s3_bucket_name, Key=code_s3_key, Body=code)

            # 2. Launch the Fargate task
            response = self.ecs_client.run_task(
                cluster=self.cluster_name,
                taskDefinition=self.sandbox_task_definition,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': self.subnet_ids,
                        'securityGroups': self.security_group_ids,
                        'assignPublicIp': 'ENABLED'
                    }
                },
                overrides={
                    'containerOverrides': [{
                        'name': f"{os.getenv('PROJECT_NAME', 'davi')}-sandbox",
                        'environment': [
                            {'name': 'S3_BUCKET', 'value': self.s3_bucket_name},
                            {'name': 'DATA_S3_KEY', 'value': data_s3_key},
                            {'name': 'CODE_S3_KEY', 'value': code_s3_key},
                            {'name': 'RESULT_S3_KEY', 'value': result_s3_key},
                        ]
                    }]
                }
            )
            
            if not response.get('tasks'):
                raise RuntimeError("Failed to start Fargate task.")

            # 3. Poll S3 for the result
            timeout_seconds = 60
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                try:
                    result_obj = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=result_s3_key)
                    result_content = result_obj['Body'].read().decode('utf-8')
                    return json.loads(result_content)
                except self.s3_client.exceptions.NoSuchKey:
                    time.sleep(2) # Wait before checking again
            
            return {"error": "Execution timed out while waiting for the result."}

        except Exception as e:
            print(f"Error in execute_code_aws: {e}")
            return {"error": f"An AWS error occurred during execution: {e}"}