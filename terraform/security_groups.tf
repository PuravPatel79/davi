# 1. Security Group for the Application Load Balancer (ALB)
# This is our public-facing firewall. It allows web traffic from the internet.
resource "aws_security_group" "davi_lb_sg" {
  name        = "davi-load-balancer-sg"
  description = "Allows HTTP traffic for the davi application"
  vpc_id      = aws_vpc.davi_vpc.id # Links this SG to our VPC

  # Allow incoming HTTP traffic from anywhere on the internet
  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP from anywhere"
  }

  # Allow all outgoing traffic from the load balancer
  egress {
    protocol    = "-1" # -1 means all protocols
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "davi-lb-sg"
  }
}

# 2. Security Group for the ECS Services (Backend and Frontend)
# This firewall protects our application containers.
resource "aws_security_group" "davi_service_sg" {
  name        = "davi-service-sg"
  description = "Allows traffic from the ALB and between containers"
  vpc_id      = aws_vpc.davi_vpc.id

  # Rule 1: Allow incoming traffic from our Load Balancer to the Frontend
  ingress {
    protocol        = "tcp"
    from_port       = 80
    to_port         = 80
    security_groups = [aws_security_group.davi_lb_sg.id]
    description     = "Allow traffic from Load Balancer to Frontend"
  }

  # Rule 2: Allow communication between containers within this security group.
  # This lets the Frontend (Nginx) talk to the Backend (Flask) on port 5000.
  ingress {
    protocol    = "tcp"
    from_port   = 5000
    to_port     = 5000
    self        = true # 'self = true' means "from other resources in this same security group"
    description = "Allow Frontend to Backend communication within ECS"
  }
  
  # Allow all outgoing traffic
  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "davi-service-sg"
  }

  # This lifecycle block tells Terraform to ignore changes to the description, preventing it from trying to replace the security group.
  lifecycle {
    ignore_changes = [description]
  }
}