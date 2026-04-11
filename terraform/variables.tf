variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-1"
}

variable "instance_type" {
  description = "EC2 instance type (default: t3.large for Selenium stability)"
  type        = string
  default     = "t3.large"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
  sensitive   = false
}

variable "vpc_id" {
  description = "VPC ID where the instance will be launched"
  type        = string
  default     = null # Will use default VPC if not specified
}

variable "subnet_id" {
  description = "Subnet ID where the instance will be launched"
  type        = string
  default     = null # Will use default subnet if not specified
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 30
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"] # ⚠️ Change to your IP or range for security
}

variable "allowed_app_cidrs" {
  description = "CIDR blocks allowed for application access (Selenium, noVNC)"
  type        = list(string)
  default     = ["0.0.0.0/0"] # ⚠️ Change to your IP or range for security
}

variable "github_repo_url" {
  description = "GitHub repository URL to clone (required)"
  type        = string
}

variable "repo_branch" {
  description = "Git branch to checkout"
  type        = string
  default     = "main"
}

variable "instance_profile_name" {
  description = "IAM instance profile name (optional)"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "Optional S3 bucket name for downloaded templates"
  type        = string
  default     = ""
}

variable "s3_key_prefix" {
  description = "S3 key prefix under which session folders will be stored"
  type        = string
  default     = "selenium-templates"
}

variable "environment_vars" {
  description = "Environment variables for Docker Compose"
  type        = map(string)
  default = {
    SELENIUM_REMOTE_URL = "http://selenium:4444"
    TARGET_URL          = "https://www.google.com/"
    WAIT_SECONDS        = "10"
  }
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "selenium-webdriver"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}
