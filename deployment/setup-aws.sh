#!/bin/bash

# AWS Setup Script for Strands A2A Server
# This script automates the creation of AWS resources needed for deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-1}"
SECRET_NAME="strands-a2a/credentials"
POLICY_NAME="StrandsA2ASecretsAccess"
ROLE_NAME="StrandsA2AServerRole"
INSTANCE_PROFILE_NAME="StrandsA2AServerProfile"

echo -e "${GREEN}=== Strands A2A AWS Setup ===${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Please install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}ERROR: jq is not installed${NC}"
    echo "Please install it: brew install jq (macOS) or apt-get install jq (Ubuntu)"
    exit 1
fi

echo -e "${YELLOW}Step 1: Collecting credentials${NC}"
echo ""

read -p "Enter your API_PASSWORD: " API_PASSWORD
read -p "Enter your LLM_SERVICE_API_KEY: " LLM_SERVICE_API_KEY
read -p "Enter your LLM_SERVICE_ENDPOINT [https://lite-llm.mymaas.net]: " LLM_ENDPOINT
LLM_ENDPOINT=${LLM_ENDPOINT:-https://lite-llm.mymaas.net}

echo ""
echo -e "${YELLOW}Step 2: Creating secret in AWS Secrets Manager${NC}"

# Check if secret already exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &> /dev/null; then
    echo "Secret already exists. Updating..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "{\"API_PASSWORD\":\"$API_PASSWORD\",\"LLM_SERVICE_API_KEY\":\"$LLM_SERVICE_API_KEY\",\"LLM_SERVICE_ENDPOINT\":\"$LLM_ENDPOINT\"}" \
        --region "$REGION"
    echo -e "${GREEN}✓ Secret updated${NC}"
else
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Credentials for Strands A2A Server" \
        --secret-string "{\"API_PASSWORD\":\"$API_PASSWORD\",\"LLM_SERVICE_API_KEY\":\"$LLM_SERVICE_API_KEY\",\"LLM_SERVICE_ENDPOINT\":\"$LLM_ENDPOINT\"}" \
        --region "$REGION"
    echo -e "${GREEN}✓ Secret created${NC}"
fi

SECRET_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" --query 'ARN' --output text)
echo "Secret ARN: $SECRET_ARN"

echo ""
echo -e "${YELLOW}Step 3: Creating IAM policy${NC}"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

# Check if policy already exists
POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"
if aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
    echo "Policy already exists: $POLICY_ARN"
else
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://"$SCRIPT_DIR/ec2-iam-policy.json" \
        --description "Allow EC2 instance to read Strands A2A secrets" \
        > /dev/null
    echo -e "${GREEN}✓ Policy created${NC}"
fi
echo "Policy ARN: $POLICY_ARN"

echo ""
echo -e "${YELLOW}Step 4: Creating IAM role${NC}"

# Create trust policy
TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

# Check if role already exists
if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo "Role already exists: $ROLE_NAME"
else
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "IAM role for Strands A2A EC2 instance" \
        > /dev/null
    echo -e "${GREEN}✓ Role created${NC}"
fi

# Attach policy to role
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$POLICY_ARN" 2>/dev/null || true
echo -e "${GREEN}✓ Policy attached to role${NC}"

echo ""
echo -e "${YELLOW}Step 5: Creating instance profile${NC}"

# Check if instance profile already exists
if aws iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" &> /dev/null; then
    echo "Instance profile already exists: $INSTANCE_PROFILE_NAME"
else
    aws iam create-instance-profile \
        --instance-profile-name "$INSTANCE_PROFILE_NAME" \
        > /dev/null

    # Wait a moment for the instance profile to be created
    sleep 2

    aws iam add-role-to-instance-profile \
        --instance-profile-name "$INSTANCE_PROFILE_NAME" \
        --role-name "$ROLE_NAME"

    echo -e "${GREEN}✓ Instance profile created${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Create a security group with ports 22, 9000, and 9001 open"
echo "2. Launch an EC2 instance with IAM instance profile: $INSTANCE_PROFILE_NAME"
echo "3. Use the user data script from deployment/DEPLOYMENT.md"
echo ""
echo "Resources created:"
echo "  - Secret: $SECRET_ARN"
echo "  - Policy: $POLICY_ARN"
echo "  - Role: $ROLE_NAME"
echo "  - Instance Profile: $INSTANCE_PROFILE_NAME"
echo ""
echo "For detailed deployment instructions, see: deployment/DEPLOYMENT.md"
