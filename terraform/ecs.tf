# 1. ECS Cluster
# A logical grouping for our services and tasks.
resource "aws_ecs_cluster" "davi_cluster" {
  name = "${var.project_name}-cluster"

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# 2. CloudWatch Log Group
# A destination for the logs from all our containers.
resource "aws_cloudwatch_log_group" "davi_log_group" {
  name = "/ecs/${var.project_name}"

  tags = {
    Name = "${var.project_name}-log-group"
  }
}

# 3. IAM Role for ECS Task Execution
# This role grants the ECS agent permissions to make AWS API calls on your behalf.
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# 4. ECS Task Definition
# This is the blueprint for davi. It defines the containers that form our task.
resource "aws_ecs_task_definition" "davi_task" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc" # Required for Fargate
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024" # 1 vCPU
  memory                   = "2048" # 2GB RAM
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  # This is the JSON array that defines the containers in our task.
  container_definitions = jsonencode([
    # Frontend Container Definition
    {
      name      = "${var.project_name}-frontend"
      image     = "${aws_ecr_repository.davi_frontend_ecr.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
        }
      ],
      # Setting the environment variable for AWS
      environment = [
        {
          name  = "backend_host_api"
          value = "localhost"
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.davi_log_group.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    },
    # Backend Container Definition
    {
      name      = "${var.project_name}-backend"
      image     = "${aws_ecr_repository.davi_backend_ecr.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 5000
        }
      ],
      environment = [
        {
          name  = "GOOGLE_API_KEY"
          value = var.gemini_api_key
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.davi_log_group.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      },
      dependsOn = [
        {
          containerName = "redis"
          condition     = "START"
        }
      ]
    },
    # Redis Container Definition
    {
      name      = "redis"
      image     = "redis:alpine"
      essential = true
      portMappings = [
        {
          containerPort = 6379
          hostPort      = 6379
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.davi_log_group.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "redis"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-task-definition"
  }
}

# 5. ECS Service
# This launches and maintains task definition in the specified cluster.
resource "aws_ecs_service" "davi_service" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.davi_cluster.id
  task_definition = aws_ecs_task_definition.davi_task.arn
  desired_count   = 1 # Run one instance of the task
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.davi_public_subnet_1.id, aws_subnet.davi_public_subnet_2.id]
    security_groups = [aws_security_group.davi_service_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.davi_frontend_tg.arn
    container_name   = "${var.project_name}-frontend"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.davi_http_listener]

  tags = {
    Name = "${var.project_name}-service"
  }
}