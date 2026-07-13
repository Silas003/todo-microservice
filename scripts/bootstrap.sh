#!/usr/bin/env bash
# One-time setup: S3 artifact bucket, GitHub OIDC provider (idempotent),
# and the cicd CloudFormation stack that creates the GitHub Actions deploy role.
set -euo pipefail

REGION="${1:-eu-central-1}"
GITHUB_ORG="${2:?Usage: $0 <region> <github-org> <github-repo-name>}"
GITHUB_REPO_NAME="${3:?Usage: $0 <region> <github-org> <github-repo-name>}"
ENVIRONMENT="dev"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="sam-artifacts-${ACCOUNT_ID}-${REGION}"

# ── Step 1: S3 artifact bucket ────────────────────────────────────────────────
echo "==> [1/3] S3 artifact bucket: ${BUCKET_NAME}"
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
  echo "    Already exists, skipping."
else
  aws s3api create-bucket \
    --bucket "${BUCKET_NAME}" \
    --region "${REGION}" \
    --create-bucket-configuration LocationConstraint="${REGION}"
  aws s3api put-bucket-versioning \
    --bucket "${BUCKET_NAME}" \
    --versioning-configuration Status=Enabled
  echo "    Created."
fi

echo ""
echo "==> [2/3] Writing s3_bucket to samconfig.toml"
if grep -q "s3_bucket" samconfig.toml; then
  sed -i.bak "s|s3_bucket = .*|s3_bucket = \"${BUCKET_NAME}\"|" samconfig.toml
else
  sed -i.bak "/^\[default.deploy.parameters\]/a s3_bucket = \"${BUCKET_NAME}\"" samconfig.toml
fi
rm -f samconfig.toml.bak

# ── Step 2: GitHub OIDC provider (account-wide singleton) ────────────────────
echo ""
echo "==> [2/3] GitHub OIDC provider"
OIDC_ARN=$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?ends_with(Arn,'token.actions.githubusercontent.com')].Arn" \
  --output text)

if [ -z "${OIDC_ARN}" ] || [ "${OIDC_ARN}" = "None" ]; then
  echo "    Creating..."
  OIDC_ARN=$(aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
    --query OpenIDConnectProviderArn \
    --output text)
  echo "    Created: ${OIDC_ARN}"
else
  echo "    Already exists: ${OIDC_ARN}"
fi

# ── Step 3: cicd stack (deploy IAM role) ─────────────────────────────────────
echo ""
echo "==> [3/3] Deploying cicd stack (GitHub Actions IAM role)"
CICD_PACKAGED="/tmp/cicd-packaged-${ENVIRONMENT}.yaml"
aws cloudformation package \
  --template-file stacks/cicd.yaml \
  --s3-bucket "${BUCKET_NAME}" \
  --output-template-file "${CICD_PACKAGED}" \
  --region "${REGION}"

aws cloudformation deploy \
  --template-file "${CICD_PACKAGED}" \
  --stack-name "todo-cicd-${ENVIRONMENT}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${REGION}" \
  --parameter-overrides \
    GitHubOrg="${GITHUB_ORG}" \
    GitHubRepoName="${GITHUB_REPO_NAME}" \
    Environment="${ENVIRONMENT}" \
    OIDCProviderArn="${OIDC_ARN}"

DEPLOY_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "todo-cicd-${ENVIRONMENT}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`DeployRoleArn`].OutputValue' \
  --output text)

echo ""
echo "======================================================"
echo "Bootstrap complete."
echo ""
echo "Add these secrets to your GitHub repository:"
echo "  AWS_DEPLOY_ROLE_ARN  = ${DEPLOY_ROLE_ARN}"
echo "  GITHUB_REPO_URL      = https://github.com/${GITHUB_ORG}/${GITHUB_REPO_NAME}"
echo "  AMPLIFY_OAUTH_TOKEN  = <GitHub PAT with repo scope>"
echo "======================================================"
