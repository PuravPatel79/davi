import os
import sys
import json
import boto3
import subprocess
import traceback

# Configuration
# These environment variables are passed in by the main application's Fargate task definition.
S3_BUCKET = os.getenv("S3_BUCKET")
DATA_S3_KEY = os.getenv("DATA_S3_KEY")
CODE_S3_KEY = os.getenv("CODE_S3_KEY")
RESULT_S3_KEY = os.getenv("RESULT_S3_KEY")

# Local File Paths within the container
LOCAL_DATA_PATH = "/home/appuser/data.csv"
LOCAL_CODE_PATH = "/home/appuser/script.py"

def run_sandbox_execution():
    """
    The main entry point for the sandbox Fargate task.
    It orchestrates downloading, executing, and uploading the results.
    """
    s3_client = boto3.client("s3")
    result_payload = {}

    try:
        # 1. Download the dataset and the user's code from S3
        print(f"Downloading data from s3://{S3_BUCKET}/{DATA_S3_KEY}")
        s3_client.download_file(S3_BUCKET, DATA_S3_KEY, LOCAL_DATA_PATH)

        print(f"Downloading code from s3://{S3_BUCKET}/{CODE_S3_KEY}")
        s3_client.download_file(S3_BUCKET, CODE_S3_KEY, LOCAL_CODE_PATH)
        print("Downloads complete.")

        # 2. Execute the user's code in a separate process
        print(f"Executing user script: {LOCAL_CODE_PATH}")
        
        process = subprocess.run(
            [sys.executable, LOCAL_CODE_PATH],
            capture_output=True,
            text=True,
            check=False,  # We set check to False to handle non-zero exit codes ourselves
            timeout=60    # A hard timeout for the subprocess
        )

        # 3. Process the result
        if process.returncode == 0:
            print("Execution successful.")
            output_str = process.stdout.strip()
            # Determine if the output is a Plotly JSON or plain text
            try:
                json.loads(output_str)
                result_payload['output'] = {"type": "visualization", "data": output_str}
            except json.JSONDecodeError:
                result_payload['output'] = {"type": "text", "data": output_str}
        else:
            print(f"Execution failed with exit code {process.returncode}.")
            error_message = process.stderr.strip()
            if process.stdout.strip():
                error_message = f"{process.stdout.strip()}\n{error_message}"
            result_payload['error'] = error_message if error_message else "Script failed with no error message."

    except subprocess.TimeoutExpired:
        print("Execution timed out.")
        result_payload['error'] = "Execution timed out after 60 seconds."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        result_payload['error'] = f"An internal sandbox error occurred: {traceback.format_exc()}"

    finally:
        # 4. Upload the result payload back to S3
        try:
            print(f"Uploading result to s3://{S3_BUCKET}/{RESULT_S3_KEY}")
            result_body = json.dumps(result_payload)
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=RESULT_S3_KEY,
                Body=result_body,
                ContentType='application/json'
            )
            print("Result upload complete.")
        except Exception as upload_error:
            print(f"FATAL: Could not upload result to S3. Error: {upload_error}")


if __name__ == "__main__":
    if not all([S3_BUCKET, DATA_S3_KEY, CODE_S3_KEY, RESULT_S3_KEY]):
        print("Error: Missing one or more required environment variables.")
        sys.exit(1)
    run_sandbox_execution()