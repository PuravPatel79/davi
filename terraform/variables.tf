# Defines a variable for the project name, which we can reuse in various resources.
variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "davi"
}

# Defines a variable for the AWS region.
variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "us-east-2"
}

# Defines a variable for the Gemini API Key.
# You will be prompted to enter this when you run 'terraform apply'.
variable "gemini_api_key" {
  description = "The Google Gemini API key for the backend service"
  type        = string
  sensitive   = true # Marking the variable as sensitive to avoid showing it in logs
}