#!/usr/bin/env bash
set -euo pipefail

REGION="ap-southeast-1"
KEY_NAME="selenium-key"
REPO_URL=""
REPO_BRANCH="main"
FORCE_PROVISION="false"

usage() {
  cat <<'EOF'
Usage:
  ./start_fast.sh --repo <github_repo_url> [--key <key_pair_name>] [--branch <branch>] [--force-provision]

Example:
  ./start_fast.sh --repo https://github.com/your-user/selenium-webdriver-docker.git
  ./start_fast.sh --repo https://github.com/your-user/selenium-webdriver-docker.git --force-provision
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO_URL="$2"
      shift 2
      ;;
    --key)
      KEY_NAME="$2"
      shift 2
      ;;
    --branch)
      REPO_BRANCH="$2"
      shift 2
      ;;
    --force-provision)
      FORCE_PROVISION="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$REPO_URL" ]]; then
  echo "Error: --repo is required"
  usage
  exit 1
fi

if [[ ! "$REPO_URL" =~ ^https://github\.com/.+\.git$ ]]; then
  echo "Error: --repo must be a GitHub HTTPS URL ending with .git"
  echo "Example: --repo https://github.com/your-user/your-repo.git"
  exit 1
fi

for cmd in aws terraform curl ssh tar; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' is not installed"
    exit 1
  fi
done

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$ROOT_DIR/terraform"
PEM_PATH="$HOME/.ssh/${KEY_NAME}.pem"

# Ensure SSH directory exists for PEM output
mkdir -p "$HOME/.ssh"

cd "$TF_DIR"

echo "[1/9] Validating AWS credentials..."
aws sts get-caller-identity >/dev/null

echo "[2/9] Ensuring EC2 key pair exists in $REGION..."
if aws ec2 describe-key-pairs --region "$REGION" --key-names "$KEY_NAME" >/dev/null 2>&1; then
  echo "Key pair '$KEY_NAME' already exists."
  if [[ ! -f "$PEM_PATH" ]]; then
    echo "Warning: $PEM_PATH does not exist."
    echo "If this key was created earlier, use the original .pem file you saved at creation time."
  fi
else
  echo "Creating key pair '$KEY_NAME'..."
  aws ec2 create-key-pair \
    --key-name "$KEY_NAME" \
    --region "$REGION" \
    --query 'KeyMaterial' \
    --output text > "$PEM_PATH"
  chmod 400 "$PEM_PATH"
  echo "Saved: $PEM_PATH"
fi

echo "[3/9] Terraform init..."
terraform init -input=false >/dev/null

deploy_exists="false"
IP="$(terraform output -raw instance_public_ip 2>/dev/null || true)"

# Consider deployment existing only when we have a valid IPv4 output.
if [[ "$IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  deploy_exists="true"
fi

if [[ "$deploy_exists" == "true" && "$FORCE_PROVISION" != "true" ]]; then
  WEB_URL="$(terraform output -raw web_app_url)"
  NOVNC_URL="$(terraform output -raw novnc_url)"

  echo "[4/9] Existing deployment found. Updating app in-place on $IP (URL stays unchanged)..."

  if [[ ! -f "$PEM_PATH" ]]; then
    echo "Error: missing SSH key at $PEM_PATH"
    echo "Create/import the PEM first, or rerun with correct --key"
    exit 1
  fi

  tar \
    --exclude='.git' \
    --exclude='terraform/.terraform' \
    --exclude='terraform/terraform.tfstate' \
    --exclude='terraform/terraform.tfstate.backup' \
    --exclude='terraform/.terraform.lock.hcl' \
    --exclude='test/.venv' \
    -czf - -C "$ROOT_DIR" . | \
    ssh -o StrictHostKeyChecking=accept-new -i "$PEM_PATH" "ubuntu@$IP" \
      'set -e; rm -rf /app/*; tar -xzf - -C /app; cd /app; docker compose up -d --build'

  echo
  echo "Update complete. URL remains unchanged:"
  echo "$WEB_URL"
  echo
  echo "noVNC URL:"
  echo "$NOVNC_URL"
  exit 0
fi

echo "[4/9] Detecting your public IP..."
MY_IP="$(curl -s ifconfig.me)"
if [[ -z "$MY_IP" ]]; then
  echo "Error: could not detect public IP"
  exit 1
fi
echo "Your IP: $MY_IP"

echo "[5/9] Getting default VPC and subnet in $REGION..."
VPC_ID="$(aws ec2 describe-vpcs \
  --region "$REGION" \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' \
  --output text)"

if [[ -z "$VPC_ID" || "$VPC_ID" == "None" ]]; then
  echo "Error: no default VPC found in $REGION"
  echo "Create a VPC/subnet first, then set vpc_id and subnet_id manually in terraform.tfvars"
  exit 1
fi

SUBNET_ID="$(aws ec2 describe-subnets \
  --region "$REGION" \
  --filters Name=vpc-id,Values="$VPC_ID" \
  --query 'Subnets[0].SubnetId' \
  --output text)"

if [[ -z "$SUBNET_ID" || "$SUBNET_ID" == "None" ]]; then
  echo "Error: no subnet found in VPC $VPC_ID"
  exit 1
fi

echo "VPC: $VPC_ID"
echo "Subnet: $SUBNET_ID"

echo "[6/9] Writing terraform.tfvars..."
cat > terraform.tfvars <<EOF
aws_region    = "$REGION"
instance_type = "t3.large"
key_pair_name = "$KEY_NAME"
vpc_id        = "$VPC_ID"
subnet_id     = "$SUBNET_ID"

allowed_ssh_cidrs = ["${MY_IP}/32"]
allowed_app_cidrs = ["${MY_IP}/32"]

github_repo_url = "$REPO_URL"
repo_branch     = "$REPO_BRANCH"

root_volume_size = 30

environment_vars = {
  SELENIUM_REMOTE_URL = "http://selenium:4444"
  TARGET_URL          = "https://www.google.com/"
  WAIT_SECONDS        = "10"
}

common_tags = {
  Project     = "selenium-webdriver"
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "quick-start"
}
EOF

echo "[7/9] Terraform apply..."
terraform apply -auto-approve -input=false

echo "[8/9] Deployment complete."
echo
terraform output

echo
echo "Open this URL:"
WEB_URL="$(terraform output -raw web_app_url)"
NOVNC_URL="$(terraform output -raw novnc_url)"
echo "$WEB_URL"

echo
echo "To watch browser:"
echo "$NOVNC_URL"

echo
echo "[9/9] Waiting for services to be ready (this can take 1-3 minutes on first boot)..."
for i in $(seq 1 36); do
  if curl -fsS "$WEB_URL" >/dev/null 2>&1 && curl -fsS "$NOVNC_URL" >/dev/null 2>&1; then
    echo "Services are ready."
    break
  fi
  sleep 5
  if [[ "$i" -eq 36 ]]; then
    echo "Services are still starting. Please wait 1-2 more minutes and refresh URLs."
  fi
done

echo
echo "SSH command:"
IP="$(terraform output -raw instance_public_ip)"
echo "ssh -i $PEM_PATH ubuntu@$IP"
