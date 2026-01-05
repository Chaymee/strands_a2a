#!/bin/bash
# This script sets environment variables for the terminal session
# Usage: source ./litellm.sh or . ./litellm.sh

# Export environment variables
export LLM_SERVICE_API_KEY="your-apikey"
export LLM_SERVICE_ENDPOINT="https://lite-llm.mymaas.net"
export API_HOST="0.0.0.0"
export export API_PASSWORD="your_secure_password_here"

# Print confirmation message
echo "Environment variables set:"
echo "LLM API KEY=$LLM_SERVICE_API_KEY"
echo "LLM ENDPOINT=$LLM_SERVICE_ENDPOINT"
echo "API HOST=$API_HOST"
echo "API PASSWORD=$API_PASSWORD"

# Add a warning if the script is executed directly instead of being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo ""
  echo "WARNING: This script should be sourced, not executed directly."
  echo "Run 'source ./litellm.sh' or '. ./litellm.sh' instead of './litellm.sh'"
  echo "The environment variables will not persist in your current shell."
fi