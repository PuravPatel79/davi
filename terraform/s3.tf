resource "aws_s3_bucket" "davi_sandbox_temp_storage" {
  bucket = "davi-sandbox-temp-storage-${random_id.bucket_id.hex}"
  force_destroy = true # For easy cleanup during development

  tags = {
    Name = "davi-sandbox-temp-storage"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "davi_sandbox_lifecycle" {
  bucket = aws_s3_bucket.davi_sandbox_temp_storage.id

  rule {
    id      = "expire-temp-files"
    status  = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 1
    }
  }
}