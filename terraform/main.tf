terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

# Security Group for EC2 instance
resource "aws_security_group" "selenium" {
  name        = "selenium-docker-sg"
  description = "Security group for Selenium Docker deployment"
  vpc_id      = var.vpc_id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  # Selenium Grid access
  ingress {
    from_port   = 4444
    to_port     = 4444
    protocol    = "tcp"
    cidr_blocks = var.allowed_app_cidrs
  }

  # noVNC access for viewing
  ingress {
    from_port   = 7901
    to_port     = 7901
    protocol    = "tcp"
    cidr_blocks = var.allowed_app_cidrs
  }

  # Flask web app access
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = var.allowed_app_cidrs
  }

  # HTTP access (if using nginx reverse proxy)
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_app_cidrs
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "selenium-docker-sg"
  }
}

# EC2 Instance
resource "aws_instance" "selenium" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.selenium.id]
  iam_instance_profile   = var.instance_profile_name

  # User data script to setup Docker and deploy application
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    github_repo_url = var.github_repo_url
    repo_branch     = var.repo_branch
    environment_vars = var.environment_vars
  }))

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
  }

  monitoring = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tags = merge(
    var.common_tags,
    {
      Name = "selenium-webdriver-docker"
    }
  )

  lifecycle {
    ignore_changes = [ami]
  }
}

# Data source to get the latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# Elastic IP for the instance (optional but recommended)
resource "aws_eip" "selenium" {
  instance = aws_instance.selenium.id
  domain   = "vpc"

  depends_on = [aws_instance.selenium]

  tags = merge(
    var.common_tags,
    {
      Name = "selenium-webdriver-eip"
    }
  )
}
