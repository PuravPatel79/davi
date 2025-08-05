# davi - Data Analyst and Visualizer

`davi` is a powerful, full-stack data analysis application that allows users to upload datasets and interact with them using natural language. It can generate insights, create interactive visualizations, and translate plain English into SQL queries through an intuitive web interface. The application is designed with a modern, scalable architecture, ready for local development via Docker or full cloud deployment on AWS.

## Table of Contents

- [Features](#features)
- [Live Demo](#live-demo)
- [Project Architecture](#project-architecture)
- [File Structure](#file-structure)
- [Getting Started: Running 'davi'](#getting-started-running-davi)
  - [Method 1: Command-Line Tool (Backend Only)](#method-1-command-line-tool-backend-only)
  - [Method 2: Local Web Application (via Docker Compose)](#method-2-local-web-application-via-docker-compose)
  - [Method 3: Cloud Deployment (via Terraform & AWS)](#method-3-cloud-deployment-via-terraform--aws)
- [Prerequisites & Dependencies](#prerequisites--dependencies)
- [Environment Variables](#environment-variables)
- [Backend Capabilities](#backend-capabilities)

## Features

- **Full-Stack Web Interface**: An intuitive and responsive frontend built with React for seamless user interaction.
- **Natural Language Data Analysis**: Ask questions about your data in plain English ("What were the total sales?").
- **Interactive Visualizations**: Generate Plotly charts from natural language requests ("Plot sales by country").
- **NLP to SQL Conversion**: Translate complex questions into production-ready SQL queries.
- **Multiple Deployment Options**: Run as a simple CLI tool, a full-stack local instance with Docker, or a scalable cloud service on AWS.
- **Containerized Architecture**: Uses Docker and Docker Compose for consistent, isolated local development.
- **Infrastructure as Code (IaC)**: The entire cloud infrastructure is defined and managed using Terraform for repeatable, automated deployments.
- **Scalable Cloud Architecture**: Deployed on AWS ECS Fargate with an Application Load Balancer for high availability and scalability.

## Live Demo

Once deployed on AWS, the application is accessible via the Application Load Balancer's public DNS.

- **URL**: The `alb_dns_name` output from your Terraform deployment.
- **Functionality**:
  1. Load a dataset using a public URL (e.g., a raw CSV file from GitHub).
  2. Select a mode: "Informational", "Visualization", or "Natural Language to SQL".
  3. Type your query and receive the results directly in the browser.

## Project Architecture

`davi` uses a modern, decoupled, multi-container architecture.

- **Frontend**: A React single-page application that provides the user interface.
- **Web Server / Proxy**: An Nginx container that serves the static React files and acts as a reverse proxy, forwarding API requests to the backend.
- **Backend**: A Python Flask server that exposes a REST API. It contains the core logic:
  - **DataAnalysisAgent**: The "brain" that uses the Gemini LLM to interpret queries and create analysis plans.
  - **DataProcessor**: Handles all data loading and manipulation with pandas.
  - **Visualizer**: Creates interactive charts with Plotly.
- **Session Store**: A Redis container used to cache DataFrames between requests, enabling stateful analysis sessions.
- **Cloud Platform**: AWS provides the underlying infrastructure, managed by Terraform:
  - **Compute**: AWS ECS with Fargate for serverless container orchestration.
  - **Networking**: A custom VPC with public subnets, an Internet Gateway, and an Application Load Balancer (ALB).
  - **Container Registry**: Amazon ECR to store the frontend and backend Docker images.

## File Structure

```
davi/
├── .github/              # CI/CD workflows (e.g., Jenkins, GitHub Actions)
├── backend/              # Flask backend application
│   ├── src/
│   │   ├── agent.py
│   │   ├── data_processor.py
│   │   └── visualizer.py
│   ├── .env              # Local environment variables (e.g., GOOGLE_API_KEY)
│   ├── app.py            # Main Flask application file
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React frontend application
│   ├── src/
│   │   └── App.jsx       # Main React component
│   ├── Dockerfile
│   ├── nginx.conf        # Nginx configuration for serving and proxying
│   └── package.json
├── terraform/            # All Terraform IaC files
│   ├── main.tf           # VPC, Subnets, IGW
│   ├── alb.tf            # Application Load Balancer
│   ├── ecs.tf            # ECS Cluster, Task Definition, Service
│   ├── ecr.tf            # ECR Repositories
│   ├── security_groups.tf
│   └── variables.tf
├── .gitignore
└── docker-compose.yml    # Docker Compose file for local full-stack deployment
```

## Getting Started: Running 'davi'

This application can be run in three distinct ways.

### Method 1: Command-Line Tool (Backend Only)

This is the original, lightweight method for performing quick, backend-only data analysis without a web interface.

- **Purpose:** Quick analysis, scripting, and testing the core Python logic.
- **How to Run:**
  1. Navigate to the project root, activate your Python virtual environment, and install dependencies (`pip install -r backend/requirements.txt`).
  2. Ensure your `GOOGLE_API_KEY` is set as an environment variable or is in a `.env` file.
  3. Run the main script:
     ```bash
     python main.py
     ```

### Method 2: Local Web Application (via Docker Compose)

This method runs the complete full-stack application (Frontend, Backend, Redis) on your local machine using containers. This is the standard way to develop and test.

- **Purpose:** Local development and testing of the full application in a production-like environment.
- **How to Run:**
  1. Ensure Docker Desktop is installed and running.
  2. Create a `.env` file in the `backend/` directory with your `GOOGLE_API_KEY`.
  3. From the project root directory, run the command:
     ```bash
     docker-compose up --build
     ```
  4. Access the application in your web browser at: **`http://localhost:3000`**

### Method 3: Cloud Deployment (via Terraform & AWS)

This method builds the entire cloud infrastructure from scratch and deploys the application for public access.

- **Purpose:** Deploying the application to a live, production environment.
- **How to Run:**
  1. **Build and Push Docker Images:** You must first build your local Docker images and push them to the ECR repositories that Terraform will create.
  2. **Deploy the Infrastructure:**
     - Navigate to the `/terraform` directory.
     - Run `terraform init`.
     - Run `terraform apply`. You will be prompted to enter your `gemini_api_key`.
  3. **Access the Live Application:**
     - Once `terraform apply` is complete, it will display the `alb_dns_name` in the outputs.
     - Paste this DNS name into your web browser to access your application.

## Prerequisites & Dependencies

- **System-Level:**
  - Python 3.8+
  - Node.js (for frontend development)
  - Docker & Docker Compose
  - Terraform
  - AWS CLI
- **Backend (Python):** See `backend/requirements.txt`. Key libraries include `Flask`, `pandas`, `google-generativeai`, and `redis`.
- **Frontend (JavaScript):** See `frontend/package.json`. Key libraries include `react` and `plotly.js`.

## Environment Variables

- `GOOGLE_API_KEY`: **Required.** Your API key for the Google Gemini service.
  - For Docker/local development, place it in `backend/.env`.
  - For AWS deployment, Terraform will prompt you for it securely.

## Backend Capabilities

The backend processing engine supports a wide range of operations:

- **Filtering:** Equality (`==`), inequality (`!=`), comparisons (`>`, `<`, `>=`, `<=`), and list inclusion/exclusion (`in`, `not in`).
- **Aggregation Functions:** `sum`, `mean`, `count`, `min`, `max`, `size`.
- **Visualization Types:** Bar charts, line charts, scatter plots, histograms, pie charts, box plots, and heatmaps.