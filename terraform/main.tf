provider "aws" {
  region = "us-east-2"
}

# Creates a new Virtual Private Cloud (VPC) for davi.
# This provides a logically isolated section of the AWS Cloud.
resource "aws_vpc" "davi_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "davi-vpc"
  }
}

# Creates two public subnets within our VPC.
# Subnets allow me to partition the network inside the VPC.
# Our containers will run in these subnets.
resource "aws_subnet" "davi_public_subnet_1" {
  vpc_id            = aws_vpc.davi_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-2a"

  tags = {
    Name = "davi-public-subnet-1"
  }
}

resource "aws_subnet" "davi_public_subnet_2" {
  vpc_id            = aws_vpc.davi_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-2b"

  tags = {
    Name = "davi-public-subnet-2"
  }
}

# Creates an Internet Gateway to allow communication between our VPC and the internet.
resource "aws_internet_gateway" "davi_igw" {
  vpc_id = aws_vpc.davi_vpc.id

  tags = {
    Name = "davi-igw"
  }
}

# Creates a route table to direct outbound traffic from our subnets to the Internet Gateway.
resource "aws_route_table" "davi_route_table" {
  vpc_id = aws_vpc.davi_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.davi_igw.id
  }

  tags = {
    Name = "davi-public-route-table"
  }
}

# Associates our subnets with the route table.
resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.davi_public_subnet_1.id
  route_table_id = aws_route_table.davi_route_table.id
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.davi_public_subnet_2.id
  route_table_id = aws_route_table.davi_route_table.id
}