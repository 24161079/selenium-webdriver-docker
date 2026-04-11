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

data "aws_caller_identity" "current" {}

locals {
  s3_bucket_name             = var.s3_bucket_name != "" ? var.s3_bucket_name : "selenium-webdriver-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  use_managed_instance_role  = var.instance_profile_name == ""
  managed_instance_role_name = "selenium-webdriver-ec2-role"
  managed_instance_profile   = "selenium-webdriver-ec2-profile"
}

resource "aws_s3_bucket" "templates" {
  bucket        = local.s3_bucket_name
  force_destroy = true

  tags = merge(
    var.common_tags,
    {
      Name = "selenium-webdriver-templates"
    }
  )
}

resource "aws_s3_bucket_versioning" "templates" {
  bucket = aws_s3_bucket.templates.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "templates" {
  bucket                  = aws_s3_bucket.templates.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "templates" {
  bucket = aws_s3_bucket.templates.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    sid     = "ListBucket"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.templates.arn,
    ]
  }

  statement {
    sid = "ReadWriteObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.templates.arn}/*",
    ]
  }
}

resource "aws_iam_role" "selenium" {
  count              = local.use_managed_instance_role ? 1 : 0
  name               = local.managed_instance_role_name
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = merge(
    var.common_tags,
    {
      Name = "selenium-webdriver-ec2-role"
    }
  )
}

resource "aws_iam_role_policy" "selenium_s3" {
  count  = local.use_managed_instance_role ? 1 : 0
  name   = "selenium-webdriver-s3-access"
  role   = aws_iam_role.selenium[0].id
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_instance_profile" "selenium" {
  count = local.use_managed_instance_role ? 1 : 0
  name  = local.managed_instance_profile
  role  = aws_iam_role.selenium[0].name
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
  iam_instance_profile   = local.use_managed_instance_role ? aws_iam_instance_profile.selenium[0].name : var.instance_profile_name

  # User data script to setup Docker and deploy application
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    github_repo_url = var.github_repo_url
    repo_branch     = var.repo_branch
    environment_vars = merge(
      var.environment_vars,
      {
        AWS_REGION         = var.aws_region
        AWS_DEFAULT_REGION = var.aws_region
        S3_BUCKET          = aws_s3_bucket.templates.bucket
        S3_KEY_PREFIX      = var.s3_key_prefix
      }
    )
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
