# davi - Data Analyst and Visualizer

`davi` is a powerful, full-stack data analysis application that allows users to upload datasets and interact with them using natural language. It can generate insights, create interactive visualizations, and translate plain English into SQL queries through an intuitive web interface.

This project is a showcase of a modern, cloud-native web application. It is fully containerized with Docker and deployed on a scalable, serverless infrastructure on AWS, which is defined entirely as code using Terraform.

## Table of Contents

- [Features](#features)
- [Project Architecture](#project-architecture)
- [Project Status & Roadmap](#project-status--roadmap)
- [Prerequisites & Dependencies](#prerequisites--dependencies)
- [Environment Variables](#environment-variables)
- [Getting Started: Running 'davi'](#getting-started-running-davi)
  - [Method 1: Command-Line Tool (Backend Only)](#method-1-command-line-tool-backend-only)
  - [Method 2: Local Web Application (via Docker Compose)](#method-2-local-web-application-via-docker-compose)
  - [Method 3: Cloud Deployment on AWS](#method-3-cloud-deployment-on-aws)
- [Usage](#usage)
  - [Command-Line Interface](#command-line-interface)
  - [Web Application (Docker & AWS)](#web-application-docker--aws)
- [File Structure](#file-structure)
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

## Project Status & Roadmap

The project is currently at the end of Phase 5.

- **Phase 1: Backend API** - **Complete**
- **Phase 2: Frontend UI** - **Complete**
- **Phase 3: Containerization** - **Complete**
- **Phase 4: Cloud Deployment** - **Complete**
- **Phase 5: Automation & CI/CD** - **Complete**
- **Phase 6: Scaling & Advanced Features** - **Next Up:** Future work includes migrating to Kubernetes for advanced scaling and adding features like user accounts and query history with a persistent database (PostgreSQL/MongoDB).

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

- **Required.** Your API key for the Google Gemini service.
  - For Docker/local development, create a `.env` file in the `/backend` directory and add the variable: `GOOGLE_API_KEY="your_api_key_here"`.
  - For the CI/CD pipeline, clone and create the GitHub repository with a repository secret named `GOOGLE_API_KEY`.

## Getting Started: Running 'davi'

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

This method runs the complete full-stack application on your local machine using containers. This is the standard way to develop and test.

- **Purpose:** Local development and testing of the full application in a production-like environment.
- **How to Run:**
  1. Ensure Docker Desktop is installed and running.
  2. Create a `.env` file in the `backend/` directory with your `GOOGLE_API_KEY`.
  3. From the project root directory, run the command:
     ```bash
     docker-compose up --build
     ```
  4. Access the application in your web browser at: **`http://localhost:3000`**

### Method 3: Cloud Deployment on AWS

The application is built to be deployed to a scalable, production-ready environment on AWS. The entire cloud infrastructure is defined as code using Terraform, and deployments are fully automated with a GitHub Actions CI/CD pipeline.

- **Purpose:** To showcase a real-world, cloud-native application architecture.
- **Developer Guide:** For advanced users who wish to deploy their own instance of `davi` on a personal AWS account, a detailed guide is available. Please see: **[`docs/Deployment_Guide.md`](docs/Deployment_Guide.md)**

## Usage

### Command-Line Interface

When you run the application via `python main.py`, you will interact with it directly in your terminal.

1.  **Load Data**: The application will first prompt you to enter the path to your data file (CSV or Excel) or a URL.
2.  **Select a Mode**: After the data is loaded, you will see a menu to choose between informational queries, visualizations, or NLP-to-SQL.
3.  **Interact**: Type your question in plain English. The results will be printed to the console.

### Web Application (Docker & AWS)

The interface for the local Docker deployment and the live AWS deployment is identical.

1.  **Load Data**: Paste the URL to your dataset into the input box and click **Load Data**.
2.  **Select a Mode**: Choose your analysis mode (Informational, Visualization, or Natural Language to SQL).
3.  **Ask a Question**: Type your question into the text box and click **Ask**.
4.  **View Results**: The result will appear in the results area below.

## File Structure

davi/
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD Pipeline
├── backend/
├── docs/
│   └── Deployment_Guide.md  # New detailed guide for developers
├── ecs/
│   └── task-definition.json # Task definition template for CI/CD
├── frontend/
├── terraform/
├── .gitignore
└── docker-compose.yml

## Backend Capabilities

- **Filtering:** Equality (`==`), inequality (`!=`), comparisons (`>`, `<`, `>=`, `<=`), and list inclusion/exclusion (`in`, `not in`).
- **Aggregation Functions:** `sum`, `mean`, `count`, `min`, `max`, `size`.
- **Visualization Types:** Bar charts, line charts, scatter plots, histograms, pie charts, box plots, and heatmaps.
