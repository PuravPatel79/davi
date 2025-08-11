# Deployment Guide: 'davi' on AWS

This guide is for developers who wish to deploy their own instance of the `davi` application to a personal AWS account. This process will create live cloud resources that will incur costs but can be used with the initial AWS credits.

## 1. Prerequisites

Before you begin, ensure you have the following installed and configured on your local machine:

- **An AWS Account:** You must have an AWS account with billing enabled.
- **IAM Permissions:** The IAM user or role you use must have sufficient permissions to create all the necessary resources (VPC, ECS, ECR, ALB, IAM Roles, etc.). For simplicity, the `AdministratorAccess` policy is sufficient.
- **AWS CLI:** [Install and configure the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) with the credentials for your IAM user.
- **Terraform:** [Install Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli).
- **Docker Desktop:** [Install Docker Desktop](https://www.docker.com/products/docker-desktop/). It must be running during the deployment process.

## 2. Environment Configuration

You must provide your Google Gemini API key to the backend application.

1.  Navigate to the `/terraform` directory.
2.  Create a new file named `terraform.tfvars`. This file is listed in `.gitignore` and will not be committed to your repository.
3.  Add your API key to this file in the following format:
    ```
    gemini_api_key = "your_api_key_here"
    ```

## 3. Step-by-Step Deployment

The deployment process involves creating the container registries, pushing your images, and then deploying the full infrastructure.

### Step 1: Create the Container Registries (ECR)

First, use Terraform to create the two Amazon ECR repositories that will store your Docker images.

1.  **Initialize Terraform**: Open your terminal and navigate to the `/terraform` directory. Run:
    ```bash
    terraform init
    ```
2.  **Apply and Get URLs**: Run `terraform apply`. After the command completes, Terraform will output the repository URLs. Copy the `frontend_ecr_repository_url` and `backend_ecr_repository_url` values.

### Step 2: Build and Push the Docker Images

Next, build the `frontend` and `backend` Docker images and push them to the ECR repositories you just created.

1.  **Authenticate Docker with ECR**: In your terminal, run the following AWS CLI command to allow Docker to connect to your Amazon ECR. Replace `us-east-2` with your AWS region if it's different.
    ```bash
    aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin your_aws_account_id.dkr.ecr.us-east-2.amazonaws.com
    ```
2.  **Build and Push Backend Image**:
    - Navigate to the root directory.
    - Run the `docker tag` command, replacing `[backend_ecr_repository_url]` with the URL you copied.
        ```bash
        docker tag davi-backend [backend_ecr_repository_url]:latest
        ```
    - Push the image to ECR:
        ```bash
        docker push [backend_ecr_repository_url]:latest
        ```
3.  **Build and Push Frontend Image**:
    - Navigate to/Stay in the root directory.
    - Run the `docker tag` command, replacing `[frontend_ecr_repository_url]` with the URL you copied.
        ```bash
        docker tag davi-frontend [frontend_ecr_repository_url]:latest
        ```
    - Push the image to ECR:
        ```bash
        docker push [frontend_ecr_repository_url]:latest
        ```

### Step 3: Deploy the Full Application Infrastructure

With your images now available in ECR, you can deploy the rest of the AWS infrastructure.

1.  Navigate back to the `/terraform` directory.
2.  Run the apply command again:
    ```bash
    terraform apply
    ```
    This will create the VPC, ALB, and the ECS service, which will pull your images from ECR and start the application containers. This process may take several minutes.

### Step 4: Access Your Application

Once `terraform apply` successfully completes, it will display the public URL for your application.

1.  Find the `alb_dns_name` in the `Outputs` section of your terminal.
2.  Copy this DNS name and paste it into your web browser. Your own instance of `davi` is now live.

## 4. Managing and Destroying the Infrastructure

To avoid ongoing AWS costs, you can destroy all the resources created by Terraform when you are finished.

1.  Navigate to the `/terraform` directory.
2.  Run the destroy command:
    ```bash
    terraform destroy
    ```
3.  Type `yes` when prompted to confirm the deletion.