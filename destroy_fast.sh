#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$ROOT_DIR/terraform"
DESTROY_ALL="false"

usage() {
  cat <<'EOF'
Usage:
  ./destroy_fast.sh --all

Notes:
  - Default behavior is safe: it does NOT destroy infrastructure.
  - Use --all only when you intentionally want to delete EC2/EIP and change URL.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      DESTROY_ALL="true"
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

for cmd in terraform; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: '$cmd' is not installed"
    exit 1
  fi
done

cd "$TF_DIR"

if [[ ! -f "terraform.tfstate" ]]; then
  echo "No terraform.tfstate found in $TF_DIR"
  echo "Nothing to destroy from this folder."
  exit 0
fi

if [[ "$DESTROY_ALL" != "true" ]]; then
  echo "Safe mode: no infrastructure destroyed."
  echo "To keep one stable URL, avoid destroying AWS resources."
  echo "Use ./start_fast.sh to update code in-place on existing instance."
  echo "If you still want full destroy, run: ./destroy_fast.sh --all"
  exit 0
fi

echo "Destroying Terraform resources..."
terraform destroy -auto-approve -input=false

echo "Done. All managed resources were destroyed."
