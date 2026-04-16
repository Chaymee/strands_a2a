#!/bin/bash

# Strands A2A Server Startup Script
# Fetches secrets from AWS Secrets Manager and starts the multi-agent server

set -e  # Exit on error

# Configuration
SECRET_NAME="strands-a2a/credentials"
REGION="${AWS_REGION:-us-east-2}"  # Default to us-east-2 if not set

echo "Fetching secrets from AWS Secrets Manager..."

# Fetch secrets from AWS Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query SecretString \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to fetch secrets from AWS Secrets Manager"
    echo "$SECRET_JSON"
    exit 1
fi

# Parse and export environment variables
export API_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.API_PASSWORD')
export LLM_SERVICE_API_KEY=$(echo "$SECRET_JSON" | jq -r '.LLM_SERVICE_API_KEY')
export LLM_SERVICE_ENDPOINT=$(echo "$SECRET_JSON" | jq -r '.LLM_SERVICE_ENDPOINT // "https://lite-llm.mymaas.net"')
export API_HOST="${API_HOST:-0.0.0.0}"

# Validate required secrets
if [ -z "$API_PASSWORD" ] || [ "$API_PASSWORD" = "null" ]; then
    echo "ERROR: API_PASSWORD not found in secrets"
    exit 1
fi

if [ -z "$LLM_SERVICE_API_KEY" ] || [ "$LLM_SERVICE_API_KEY" = "null" ]; then
    echo "ERROR: LLM_SERVICE_API_KEY not found in secrets"
    exit 1
fi

echo "Secrets loaded successfully"

# Set PUBLIC_URL using public IP
export PUBLIC_URL="http://$(curl -s ifconfig.me)"
echo "Using public IP for agent card: $PUBLIC_URL"

echo "Starting Strands A2A Server..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to project root directory (script is now in deploy/ subdirectory)
cd "$SCRIPT_DIR/.."

# Pull latest code from git on startup
if [ -d ".git" ]; then
    echo "Pulling latest code from git..."
    git pull || echo "Warning: git pull failed, using existing code"
fi

# Create venv if needed and install/update dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server (using module syntax for src/ structure)
exec python3 -m src.server
