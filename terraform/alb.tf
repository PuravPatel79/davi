# 1. Define the Application Load Balancer (ALB)
# This creates the main load balancer resource. It's public-facing.
resource "aws_lb" "davi_alb" {
  name               = "davi-alb"
  internal           = false # Public-facing
  load_balancer_type = "application"
  security_groups    = [aws_security_group.davi_lb_sg.id] # Attach the public-facing firewall
  subnets            = [aws_subnet.davi_public_subnet_1.id, aws_subnet.davi_public_subnet_2.id] # Place it in our public subnets

  # Enable access logs for the load balancer for monitoring and debugging
  access_logs {
    bucket  = aws_s3_bucket.lb_logs.bucket
    prefix  = "davi-lb"
    enabled = true
  }

  tags = {
    Name = "davi-alb"
  }
}

# 2. Define a Target Group
# The load balancer sends traffic to a target group. This group will contain our frontend service.
resource "aws_lb_target_group" "davi_frontend_tg" {
  name        = "davi-frontend-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.davi_vpc.id
  target_type = "ip" # Required for Fargate, as we don't manage the instances directly

  # Health checks ensure traffic is only sent to healthy containers
  health_check {
    path                = "/" # The root path of our frontend should be available
    protocol            = "HTTP"
    matcher             = "200" # Expect a 200 OK status code
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "davi-frontend-tg"
  }
}

# 3. Define a Listener
# This tells the load balancer what to do with incoming traffic.
# It "listens" for traffic on a specific port and forwards it according to the rules.
resource "aws_lb_listener" "davi_http_listener" {
  load_balancer_arn = aws_lb.davi_alb.arn # Attach to our ALB
  port              = "80"
  protocol          = "HTTP"

  # Default action: forward all traffic on port 80 to our frontend target group
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.davi_frontend_tg.arn
  }
}

# 4. Create an S3 bucket to store the load balancer's access logs
resource "aws_s3_bucket" "lb_logs" {
  bucket = "davi-alb-logs-${random_id.bucket_id.hex}" # Creates a unique bucket name
  force_destroy = true # Allow deletion even if the bucket has logs in it
}

# 5. Attach the policy to the S3 bucket
resource "aws_s3_bucket_policy" "lb_logs_policy" {
  bucket = aws_s3_bucket.lb_logs.id # Reference the bucket created above

  # Policy to allow the ALB to write logs to this bucket
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = { "AWS" = "arn:aws:iam::${data.aws_elb_service_account.main.id}:root" },
        Action    = "s3:PutObject",
        Resource  = "${aws_s3_bucket.lb_logs.arn}/davi-lb/*"
      }
    ]
  })
}


# 6. Resource to get the AWS ELB service account ID for the current region
data "aws_elb_service_account" "main" {}

# 7. Resource to generate a random suffix for the S3 bucket name to ensure it's unique
resource "random_id" "bucket_id" {
  byte_length = 8
}

# --- Outputs ---
# We'll output the DNS name of the load balancer so we can access our application
output "alb_dns_name" {
  description = "The DNS name of the Application Load Balancer"
  value       = aws_lb.davi_alb.dns_name
}