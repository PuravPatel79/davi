# 1. ECR Repository for the Frontend Application
resource "aws_ecr_repository" "davi_frontend_ecr" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-frontend-repo"
  }
}

# 2. ECR Repository for the Backend Application
resource "aws_ecr_repository" "davi_backend_ecr" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-backend-repo"
  }
}

# 3. ECR Repository for the Sandbox Application
resource "aws_ecr_repository" "davi_sandbox_ecr" {
  name                 = "${var.project_name}-sandbox"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-sandbox-repo"
  }
}

# Output the URLs of the repositories.
output "frontend_ecr_repository_url" {
  description = "The URL of the frontend ECR repository"
  value       = aws_ecr_repository.davi_frontend_ecr.repository_url
}

output "backend_ecr_repository_url" {
  description = "The URL of the backend ECR repository"
  value       = aws_ecr_repository.davi_backend_ecr.repository_url
}

output "sandbox_ecr_repository_url" {
  description = "The URL of the sandbox ECR repository"
  value       = aws_ecr_repository.davi_sandbox_ecr.repository_url
}