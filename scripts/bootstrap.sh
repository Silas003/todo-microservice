#!/usr/bin/env bash
# One-time setup: creates the SAM artifact S3 bucket, then deploys the cicd
# stack which provisions the GitHub OIDC provider and the deploy IAM role.
# All subsequent deployments run through GitHub Actions using that role.
set -euo pipefail

REGION="${1:-eu-central-1}"
GITHUB_ORG="${2:?Usage: $0 <region> <github-org> <github-repo-name>}"
GITHUB_REPO_NAME="${3:?Usage: $0 <region> <github-org> <github-repo-name>}"
ENVIRONMENT="dev"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="sam-artifacts-${ACCOUNT_ID}-${REGION}"

echo "==> [1/3] Creating SAM artifact bucket: ${BUCKET_NAME}"
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
  echo "    Already exists, skipping."
else
  if [ "${REGION}" = "us-east-1" ]; then
    aws s3 mb "s3://${BUCKET_NAME}" --region "${REGION}"
  else
    aws s3 mb "s3://${BUCKET_NAME}" --region "${REGION}" \
      --create-bucket-configuration LocationConstraint="${REGION}"
  fi
  aws s3api put-bucket-versioning \
    --bucket "${BUCKET_NAME}" \
    --versioning-configuration Status=Enabled
fi

echo ""
echo "==> [2/3] Writing s3_bucket to samconfig.toml"
if grep -q "s3_bucket" samconfig.toml; then
  sed -i.bak "s|s3_bucket = .*|s3_bucket = \"${BUCKET_NAME}\"|" samconfig.toml
else
  sed -i.bak "/^\[default.deploy.parameters\]/a s3_bucket = \"${BUCKET_NAME}\"" samconfig.toml
fi
rm -f samconfig.toml.bak

echo ""
echo "==> [3/3] Deploying cicd stack (OIDC provider + deploy IAM role)"
# Package the cicd template to a temporary location so CloudFormation can access it.
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
    Environment="${ENVIRONMENT}"

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
echo "  GITHUB_ORG           = ${GITHUB_ORG}"
echo "  GITHUB_REPO_NAME     = ${GITHUB_REPO_NAME}"
echo "  GITHUB_REPO_URL      = https://github.com/${GITHUB_ORG}/${GITHUB_REPO_NAME}"
echo "  AMPLIFY_OAUTH_TOKEN  = <GitHub PAT with repo scope>"
echo "======================================================"
