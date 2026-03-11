# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Strands A2A (Agent-to-Agent) server implementation that exposes AI agents via the A2A protocol. The project includes two agents:
- **Calculator Agent** (port 9000): Performs basic arithmetic operations
- **Factor Agent** (port 9001): Extracts numbers and returns their factors

## Project Structure

```
strands_a2a/
├── src/
│   ├── __init__.py
│   └── server.py              # Multi-agent server (self-contained)
├── tests/
│   ├── load_test.py           # Load testing script
│   └── run_load_test.sh       # Test wrapper
├── deploy/
│   ├── README.md              # Deployment guide
│   ├── start_server.sh        # Production startup script
│   ├── strands-a2a.service    # systemd service
│   ├── setup-aws.sh           # AWS setup automation
│   ├── user-data.sh           # EC2 initialization
│   └── ec2-iam-policy.json    # IAM policy
├── examples/
│   └── sample_proxy.yaml      # Solace config reference
├── README.md                  # Main documentation
├── CLAUDE.md                  # This file
└── requirements.txt
```

## Architecture

### Server Implementation

**`src/server.py`** - Multi-agent server (only execution pattern)
- Runs BOTH agents in parallel using Python multiprocessing
- Self-contained implementation with all logic inline
- Starts Calculator on port 9000, Factor on port 9001
- No separate calculator.py or factor.py files

### Agent Structure

Each agent follows this pattern:
1. Tool functions decorated with `@tool` (from Strands)
2. LiteLLM model configuration with custom endpoint
3. Strands `Agent` instance with tools
4. A2A server wrapping the agent
5. FastAPI authentication middleware (Bearer token)
6. The `/.well-known/agent-card.json` endpoint is always public (no auth required)

### Dependencies

- **strands-agents[a2a,litellm]** - Core Strands framework
- **strands-agents-tools** - Calculator tool
- **a2a-sdk[sql]** - A2A protocol implementation
- **bedrock-agentcore** - AWS Bedrock integration

## Common Commands

### Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Set required environment variables
export API_PASSWORD="your_password"
export LLM_SERVICE_API_KEY="your_key"
export LLM_SERVICE_ENDPOINT="https://lite-llm.mymaas.net"  # Optional, has default

# Run the multi-agent server (from project root)
python -m src.server
```

### Testing

```bash
# Test agent card (no auth required)
curl http://localhost:9000/.well-known/agent-card.json

# Test agent with authentication
curl -X POST http://localhost:9000 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_password" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-001",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is 10 * 11?"}],
        "messageId": "12345678-1234-1234-1234-123456789012"
      }
    }
  }'

# Run load tests
./tests/run_load_test.sh light        # Quick smoke test (10 users)
./tests/run_load_test.sh 100          # 100 concurrent users
```

## AWS Deployment

The project includes comprehensive AWS EC2 deployment infrastructure:

### Quick Deploy

```bash
cd deploy
./setup-aws.sh  # Creates all AWS resources
```

### Key Files

- **`deploy/start_server.sh`** - Production startup script
  - Fetches credentials from AWS Secrets Manager
  - Auto-pulls latest code from git on startup
  - Sets PUBLIC_URL based on EC2 metadata if available
  - Activates venv and runs `python -m src.server`

- **`deploy/README.md`** - Complete deployment guide
- **`deploy/setup-aws.sh`** - Automated AWS resource creation
- **`deploy/strands-a2a.service`** - systemd service for auto-start
- **`deploy/ec2-iam-policy.json`** - IAM policy for Secrets Manager access

### AWS Secrets

The deployment uses AWS Secrets Manager secret: `strands-a2a/credentials`

Required keys:
- `API_PASSWORD`
- `LLM_SERVICE_API_KEY`
- `LLM_SERVICE_ENDPOINT`

### Service Management (on EC2)

```bash
# View logs
sudo journalctl -u strands-a2a.service -f

# Restart service
sudo systemctl restart strands-a2a.service

# Check status
sudo systemctl status strands-a2a.service

# Update code and restart
cd /home/ubuntu/strands_a2a
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart strands-a2a.service
```

## Environment Variables

### Required
- `API_PASSWORD` - Bearer token for authentication
- `LLM_SERVICE_API_KEY` - API key for LiteLLM service

### Optional
- `LLM_SERVICE_ENDPOINT` - Default: "https://lite-llm.mymaas.net"
- `API_HOST` - Bind address, default: "0.0.0.0"
- `PUBLIC_URL` - Public URL for agent cards (auto-detected on EC2)
- `AWS_REGION` - For AWS deployments, default: "us-east-1"

## Key Design Patterns

### Multi-Process Architecture
The main server uses `multiprocessing.Process` to run agents in separate processes, allowing true parallelism.

### Authentication Pattern
All endpoints require Bearer token authentication EXCEPT `/.well-known/agent-card.json`. This is implemented via FastAPI middleware.

### LiteLLM Configuration
Agents use LiteLLM with custom endpoints configured via:
```python
LiteLLMModel(
    client_args={
        "api_base": litellm_endpoint,
        "api_key": litellm_api_key,
    },
    model_id="openai/vertex-claude-4-5-sonnet",
)
```

### Tool Return Format
Tools return dictionaries with:
```python
{
    "status": "success" | "error",
    "content": [{"text": "result text"}]
}
```

## Solace Agent Mesh Integration

The project can integrate with Solace Agent Mesh for broader agent ecosystems:
- See `examples/sample_proxy.yaml` for configuration example
- Configure proxy to point to agent endpoints (9000, 9001)
- Place config in `configs/agents` directory of Solace mesh
