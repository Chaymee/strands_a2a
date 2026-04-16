# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Strands A2A (Agent-to-Agent) server implementation that exposes AI agents via the A2A protocol. The project includes two agents:
- **Calculator Agent** (port 9000): Performs basic arithmetic operations
- **Clock Agent** (port 9001): Returns the current date and time for any timezone

## Project Structure

```
strands_a2a/
├── agents/
│   ├── calculator/                        # Standalone Calculator Agent
│   │   ├── agent.py                       # Agent logic and run() entry point
│   │   ├── __main__.py                    # python -m agents.calculator entry point
│   │   ├── requirements.txt               # Independent dependencies
│   │   └── deploy/
│   │       ├── start_server.sh            # EC2 startup script
│   │       └── strands-calculator.service # systemd service
│   └── clock/                             # Standalone Clock Agent
│       ├── agent.py                       # Agent logic and run() entry point
│       ├── __main__.py                    # python -m agents.clock entry point
│       ├── requirements.txt               # Independent dependencies
│       └── deploy/
│           ├── start_server.sh            # EC2 startup script
│           └── strands-clock.service      # systemd service
├── src/
│   ├── __init__.py
│   └── server.py                          # Local dev launcher (runs both agents)
├── tests/
│   ├── load_test.py                       # Load testing script
│   └── run_load_test.sh                   # Test wrapper
├── deploy/
│   ├── README.md                          # Deployment guide
│   ├── setup-aws.sh                       # Shared AWS IAM/Secrets setup
│   ├── ec2-iam-policy.json                # IAM policy
│   └── user-data.sh                       # EC2 initialization reference
├── examples/
│   └── sample_proxy.yaml                  # Solace config reference
├── README.md
├── CLAUDE.md
└── requirements.txt                       # Shared deps (for local dev / both agents)
```

## Architecture

### Agent Modules

Each agent lives entirely in its own directory under `agents/` and is independently deployable to a separate EC2 instance.

**`agents/calculator/agent.py`** - Calculator Agent
- Uses `strands_tools.calculator` built-in tool
- `run(port)` function is the only entry point
- Can be run standalone: `python -m agents.calculator`

**`agents/clock/agent.py`** - Clock Agent
- Uses `strands_tools.current_time` built-in tool
- `run(port)` function is the only entry point
- Can be run standalone: `python -m agents.clock`

**`src/server.py`** - Local dev multi-agent launcher only
- Imports `run` from each agent module and spawns them as separate processes
- Not used in production; each EC2 instance runs one agent directly

### Agent Structure

Each agent module follows this pattern:
1. `create_llm_model()` builds the LiteLLM model from environment variables
2. `run(port)` creates the Agent, wraps it in A2AServer, adds auth middleware, calls `uvicorn.run`
3. `/.well-known/agent-card.json` is always public (no auth required)
4. All other endpoints require `Authorization: Bearer <API_PASSWORD>`
5. `AGENT_PORT` env var overrides the default port (picked up by `__main__.py`)

### Dependencies

- **strands-agents[a2a,litellm]** - Core Strands framework
- **strands-agents-tools** - Built-in tools (calculator, current_time, etc.)
- **a2a-sdk[sql]** - A2A protocol implementation
- **bedrock-agentcore** - AWS Bedrock integration (top-level requirements.txt only)

## Common Commands

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install all dependencies (for local dev with both agents)
pip install -r requirements.txt

# Or install just what one agent needs (on a dedicated EC2 instance)
pip install -r agents/calculator/requirements.txt
pip install -r agents/clock/requirements.txt
```

### Running Locally

```bash
# Set required environment variables
export API_PASSWORD="your_password"
export LLM_SERVICE_API_KEY="your_key"
export LLM_SERVICE_ENDPOINT="https://lite-llm.mymaas.net"  # Optional, has default

# Run both agents (local dev only)
python -m src.server

# Run a single agent independently
python -m agents.calculator   # port 9000
python -m agents.clock        # port 9001

# Override port
AGENT_PORT=8080 python -m agents.calculator
```

### Testing

```bash
# Test agent card (no auth required)
curl http://localhost:9000/.well-known/agent-card.json
curl http://localhost:9001/.well-known/agent-card.json

# Test Calculator Agent
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

# Test Clock Agent
curl -X POST http://localhost:9001 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_password" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-002",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What time is it in Tokyo?"}],
        "messageId": "12345678-1234-1234-1234-123456789013"
      }
    }
  }'

# Run load tests
./tests/run_load_test.sh light        # Quick smoke test (10 users)
./tests/run_load_test.sh 100          # 100 concurrent users
```

## AWS Deployment

### Shared Setup (run once)

```bash
cd deploy
./setup-aws.sh  # Creates IAM role, instance profile, and Secrets Manager secret
```

### Deploying Calculator Agent to EC2

1. Launch an EC2 instance with the IAM instance profile from setup-aws.sh
2. SSH in and clone the repo
3. Copy the systemd service and start:

```bash
git clone <repo-url> /home/ec2-user/strands_a2a
cd /home/ec2-user/strands_a2a
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r agents/calculator/requirements.txt

sudo cp agents/calculator/deploy/strands-calculator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable strands-calculator
sudo systemctl start strands-calculator
```

### Deploying Clock Agent to EC2

Same steps but use `agents/clock/`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r agents/clock/requirements.txt
sudo cp agents/clock/deploy/strands-clock.service /etc/systemd/system/
sudo systemctl enable strands-clock
sudo systemctl start strands-clock
```

### Key Deploy Files (per agent)

- **`agents/<name>/deploy/start_server.sh`** - Fetches secrets from Secrets Manager, sets PUBLIC_URL, git pulls, creates/updates the venv with `python3.11`, and starts the agent
- **`agents/<name>/deploy/strands-<name>.service`** - systemd service (set `AGENT_PORT` here to change port)

### Service Management (on EC2)

```bash
# Calculator Agent
sudo journalctl -u strands-calculator.service -f
sudo systemctl restart strands-calculator.service
sudo systemctl status strands-calculator.service

# Clock Agent
sudo journalctl -u strands-clock.service -f
sudo systemctl restart strands-clock.service
sudo systemctl status strands-clock.service

# Update and restart
cd /home/ec2-user/strands_a2a
git pull
source .venv/bin/activate
pip install -r agents/calculator/requirements.txt  # or clock
sudo systemctl restart strands-calculator.service  # or strands-clock
```

### AWS Secrets

Both agents read from the same Secrets Manager secret: `strands-a2a/credentials`

Required keys:
- `API_PASSWORD`
- `LLM_SERVICE_API_KEY`
- `LLM_SERVICE_ENDPOINT`

## Environment Variables

### Required
- `API_PASSWORD` - Bearer token for authentication
- `LLM_SERVICE_API_KEY` - API key for LiteLLM service

### Optional
- `LLM_SERVICE_ENDPOINT` - Default: "https://lite-llm.mymaas.net"
- `API_HOST` - Bind address, default: "0.0.0.0"
- `AGENT_PORT` - Override default port (9000 for calculator, 9001 for clock)
- `PUBLIC_URL` - Public URL for agent cards (auto-detected from ifconfig.me on EC2)
- `AWS_REGION` - For AWS deployments, default: "us-east-2"

## Key Design Patterns

### Independent Agent Deployment
Each agent directory is self-contained: its own `requirements.txt`, startup script, and systemd service. You can clone the repo to an EC2 instance and run only one agent without any coupling to the other.

### Authentication Pattern
All endpoints require Bearer token authentication EXCEPT `/.well-known/agent-card.json`. Implemented via FastAPI middleware in each agent's `run()` function.

### LiteLLM Configuration
Agents use LiteLLM with custom endpoints:
```python
LiteLLMModel(
    client_args={
        "api_base": litellm_endpoint,
        "api_key": litellm_api_key,
    },
    model_id="openai/vertex-claude-4-5-sonnet",
)
```

## Solace Agent Mesh Integration

The project can integrate with Solace Agent Mesh for broader agent ecosystems:
- See `examples/sample_proxy.yaml` for configuration example
- Configure proxy to point to each agent's endpoint
- Place config in `configs/agents` directory of Solace Agent Mesh
