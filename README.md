# Selenium WebDriver Automation on AWS

This project deploys a simple web-triggered Selenium automation app to AWS EC2 using Terraform.

Region used in this guide: ap-southeast-1.

## Fastest Start (One Command)

From project root, run:

```bash
./start_fast.sh --repo https://github.com/24161079/selenium-webdriver-docker.git
```

Optional arguments:

```bash
./start_fast.sh --repo https://github.com/24161079/selenium-webdriver-docker.git --key selenium-key --branch main
./start_fast.sh --repo https://github.com/24161079/selenium-webdriver-docker.git --force-provision
```

What this script does automatically:

1. Checks AWS credentials.
2. Creates EC2 key pair (if it does not exist yet).
3. Runs `terraform init` and checks if deployment already exists.
4. If deployment exists: updates source code in-place on EC2 and restarts Docker app (URL unchanged).
5. If deployment does not exist: detects your public IP, gets default VPC/subnet, writes tfvars, and runs `terraform apply`.
6. Creates the S3 bucket for downloaded templates and grants EC2 read/write access.
7. Prints `web_app_url`, `novnc_url`, and the S3 bucket name.

Important behavior:

- For normal code updates, run `start_fast.sh` again. It reuses existing EC2/EIP so URL stays the same.
- Use `--force-provision` only when you intentionally want full provisioning flow.

## Fast Destroy (One Command)

Safe mode (default):

```bash
./destroy_fast.sh
```

This does not destroy infrastructure. It protects your stable URL from accidental deletion.

Full destroy (intentional):

```bash
./destroy_fast.sh --all
```

This runs `terraform destroy` and will remove EC2/EIP, so URL will change on next deploy.

## Run Local

To run the app on your machine, use Docker Compose from the project root:

```bash
export AWS_REGION=ap-southeast-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export S3_BUCKET=your-existing-bucket
export S3_KEY_PREFIX=selenium-templates
docker compose up -d --build
```

Then open:

- http://localhost:5000 for the web app
- http://localhost:5000/vnc for the VNC viewer page

If you only want the Flask app without Docker, you still need the Selenium container running first:

```bash
docker compose up -d selenium
export SELENIUM_REMOTE_URL=http://localhost:4444
export AWS_REGION=ap-southeast-1
export S3_BUCKET=your-existing-bucket
python app.py
```

## One-Time Prerequisites

Run these once on your machine:

```bash
# 1) Configure AWS CLI
aws configure
# Use your credentials
# Default region name: ap-southeast-1
# Default output format: json

# 2) Verify AWS login works
aws sts get-caller-identity

# 3) Verify Terraform is installed
terraform -version
```

## Deploy (Copy-Paste Steps)

Run the commands below in order.

```bash
# Move to terraform folder
cd /home/tuannka1/projects/selenium-webdriver-docker/terraform

# Create your local config file
cp terraform.tfvars.example terraform.tfvars

# Create EC2 key pair in ap-southeast-1 (if you do not already have one)
aws ec2 create-key-pair \
  --key-name selenium-key \
  --region ap-southeast-1 \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/selenium-key.pem

chmod 400 ~/.ssh/selenium-key.pem

# Get your current public IP (for security group allowlist)
MY_IP=$(curl -s ifconfig.me)
echo "$MY_IP"

# Get default VPC in ap-southeast-1
VPC_ID=$(aws ec2 describe-vpcs \
  --region ap-southeast-1 \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' \
  --output text)
echo "$VPC_ID"

# Get one subnet from that VPC
SUBNET_ID=$(aws ec2 describe-subnets \
  --region ap-southeast-1 \
  --filters Name=vpc-id,Values=$VPC_ID \
  --query 'Subnets[0].SubnetId' \
  --output text)
echo "$SUBNET_ID"
```

Now edit terraform.tfvars:

```bash
nano terraform.tfvars
```

Use this exact template inside terraform.tfvars:

```hcl
aws_region      = "ap-southeast-1"
instance_type   = "t3.large"
key_pair_name   = "selenium-key"
vpc_id          = "REPLACE_WITH_YOUR_VPC_ID"
subnet_id       = "REPLACE_WITH_YOUR_SUBNET_ID"

allowed_ssh_cidrs = ["REPLACE_WITH_YOUR_IP/32"]
allowed_app_cidrs = ["REPLACE_WITH_YOUR_IP/32"]

github_repo_url = "https://github.com/YOUR_USERNAME/YOUR_REPO.git"
repo_branch     = "main"

root_volume_size = 30

s3_bucket_name = "" # leave empty to let Terraform create a bucket automatically
s3_key_prefix  = "selenium-templates"

environment_vars = {
  SELENIUM_REMOTE_URL = "http://selenium:4444"
  TARGET_URL          = "https://www.google.com/"
  WAIT_SECONDS        = "10"
}

common_tags = {
  Project     = "selenium-webdriver"
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "your-name"
}
```

Deploy with Terraform:

```bash
terraform init
terraform plan
terraform apply -auto-approve
```

Get URLs and connection info:

```bash
terraform output
```

You should see:

- web_app_url
- novnc_url
- instance_public_ip
- s3_bucket_name
- s3_key_prefix

Open web_app_url in browser and click Start Automation.

## Useful Commands After Deploy

```bash
# SSH into EC2
ssh -i ~/.ssh/selenium-key.pem ubuntu@$(terraform output -raw instance_public_ip)

# On EC2, check containers
cd /app
docker compose ps
docker compose logs -f
docker compose logs web -f

# Verify downloaded files in container
docker compose exec -T web sh -lc 'find /app/selenium_python/score-templates -maxdepth 1 -type f | head -n 100'

# Verify files uploaded to S3 (AWS CLI must be configured)
aws s3 ls s3://YOUR_BUCKET/selenium-templates/ --recursive | tail -n 50
```

## S3 Upload Layout

- Each run gets a session folder derived from the VNC session password.
- Uploaded files are stored under `S3_KEY_PREFIX/<session-folder>/<template-folder>/`.
- Example path: `selenium-templates/session-abc123/score-templates/file.xlsx`.

## Destroy (Stop Charges)

```bash
./destroy_fast.sh
```

## Notes

- Keep terraform.tfvars private.
- Keep terraform.tfstate private.
- If your GitHub repo is private, the EC2 bootstrap clone step will fail unless authentication is added.
