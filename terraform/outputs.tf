# Outputs the ID of the VPC after it's created.
output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.davi_vpc.id
}

# Outputs the IDs of the public subnets.
output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = [aws_subnet.davi_public_subnet_1.id, aws_subnet.davi_public_subnet_2.id]
}
