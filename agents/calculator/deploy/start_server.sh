#!/bin/bash

# Calculator Agent Startup Script
# Fetches secrets from AWS Secrets Manager and starts the Calculator Agent.

set -e

SECRET_NAME="strands-a2a/credentials"
REGION="${AWS_REGION:-us-east-2}"
PORT="${AGENT_PORT:-9000}"

echo "Fetching secrets from AWS Secrets Manager..."

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

export API_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.API_PASSWORD')
export LLM_SERVICE_API_KEY=$(echo "$SECRET_JSON" | jq -r '.LLM_SERVICE_API_KEY')
export LLM_SERVICE_ENDPOINT=$(echo "$SECRET_JSON" | jq -r '.LLM_SERVICE_ENDPOINT // "https://lite-llm.mymaas.net"')
export API_HOST="${API_HOST:-0.0.0.0}"

if [ -z "$API_PASSWORD" ] || [ "$API_PASSWORD" = "null" ]; then
    echo "ERROR: API_PASSWORD not found in secrets"
    exit 1
fi

if [ -z "$LLM_SERVICE_API_KEY" ] || [ "$LLM_SERVICE_API_KEY" = "null" ]; then
    echo "ERROR: LLM_SERVICE_API_KEY not found in secrets"
    exit 1
fi

echo "Secrets loaded successfully"

export PUBLIC_URL="http://$(curl -s ifconfig.me)"
echo "Using public IP for agent card: $PUBLIC_URL"

echo "Starting Calculator Agent on port $PORT..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root is three levels up: agents/calculator/deploy/ -> root
PROJECT_ROOT="$SCRIPT_DIR/../../.."
cd "$PROJECT_ROOT"

if [ -d ".git" ]; then
    echo "Pulling latest code from git..."
    git pull || echo "Warning: git pull failed, using existing code"
fi

source "$PROJECT_ROOT/.venv/bin/activate"

export AGENT_PORT="$PORT"
exec python -m agents.calculator
