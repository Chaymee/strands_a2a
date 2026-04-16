# Strands A2A Server

A multi-agent server implementation using the Strands framework, exposing AI agents via the A2A (Agent-to-Agent) protocol.

## Overview

This project provides two intelligent agents accessible through a standardized A2A interface:

1. **Calculator Agent** (port 9000) - Performs arithmetic operations using the [Strands calculator tool](https://github.com/strands-agents/tools)
2. **Clock Agent** (port 9001) - Returns the current date and time for any timezone

Each agent is **independently deployable** to its own EC2 instance, or you can run both together for local development.

## Quick Start

### Local Development (both agents together)

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export API_PASSWORD="your_secure_password"
export LLM_SERVICE_API_KEY="your_litellm_api_key"

# 4. Run both agents
python -m src.server
```

Both agents start in separate processes:
- Calculator Agent: http://localhost:9000
- Clock Agent: http://localhost:9001

### Run a Single Agent

```bash
python -m agents.calculator   # port 9000 only
python -m agents.clock        # port 9001 only

AGENT_PORT=8080 python -m agents.calculator  # custom port
```

## Project Structure

```
strands_a2a/
├── agents/
│   ├── calculator/                        # Standalone Calculator Agent
│   │   ├── agent.py
│   │   ├── __main__.py
│   │   ├── requirements.txt
│   │   └── deploy/
│   │       ├── start_server.sh
│   │       └── strands-calculator.service
│   └── clock/                             # Standalone Clock Agent
│       ├── agent.py
│       ├── __main__.py
│       ├── requirements.txt
│       └── deploy/
│           ├── start_server.sh
│           └── strands-clock.service
├── src/
│   └── server.py              # Local dev launcher (runs both agents)
├── tests/
│   ├── load_test.py           # Load testing script
│   └── run_load_test.sh       # Test wrapper
├── deploy/
│   ├── README.md              # Detailed deployment guide
│   ├── setup-aws.sh           # Shared AWS IAM/Secrets setup (run once)
│   └── ec2-iam-policy.json    # IAM policy
└── examples/
    └── sample_proxy.yaml      # Solace Agent Mesh config reference
```

## Usage

### Testing the Agents

**Agent card (no auth required):**
```bash
curl http://localhost:9000/.well-known/agent-card.json
curl http://localhost:9001/.well-known/agent-card.json
```

**Calculator Agent:**
```bash
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
        "parts": [{"kind": "text", "text": "What is 15 * 23?"}],
        "messageId": "12345678-1234-1234-1234-123456789012"
      }
    }
  }'
```

**Clock Agent:**
```bash
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
        "messageId": "87654321-4321-4321-4321-210987654321"
      }
    }
  }'
```

### Load Testing

```bash
# Quick smoke test (10 users, 5 requests = 50 total)
./tests/run_load_test.sh -p your_password light

# 100 concurrent users against Calculator Agent
./tests/run_load_test.sh -p your_password 100

# Direct script usage against a remote server
./tests/load_test.py --url http://your-server.com:9000 --password your_password --agent calculator --users 100
```

## Configuration

### Environment Variables

**Required:**
- `API_PASSWORD` - Bearer token for API authentication
- `LLM_SERVICE_API_KEY` - API key for LiteLLM service

**Optional:**
- `LLM_SERVICE_ENDPOINT` - LiteLLM endpoint (default: `https://lite-llm.mymaas.net`)
- `API_HOST` - Bind address (default: `0.0.0.0`)
- `AGENT_PORT` - Override default port (9000 for calculator, 9001 for clock)
- `PUBLIC_URL` - Public URL for agent cards (auto-detected on EC2 via `ifconfig.me`)
- `AWS_REGION` - AWS region (default: `us-east-2`)

### AWS Secrets Manager

For AWS deployments, credentials are stored at `strands-a2a/credentials`:

```json
{
  "API_PASSWORD": "your_password",
  "LLM_SERVICE_API_KEY": "your_key",
  "LLM_SERVICE_ENDPOINT": "https://lite-llm.mymaas.net"
}
```

## AWS Deployment

Each agent can be deployed independently to its own EC2 instance. Both use the same Secrets Manager secret.

### Step 1: Shared AWS Setup (run once)

This creates the IAM role, instance profile, and Secrets Manager secret used by both agents.

```bash
cd deploy
./setup-aws.sh
```

### Step 2: Launch an EC2 Instance

- AMI: Ubuntu 22.04 LTS
- Instance type: t3.small or larger
- Attach the IAM instance profile created by `setup-aws.sh` (`StrandsA2AServerProfile`)
- Attach **both** security groups:
  - Your SSH security group (port 22)
  - `sg-09b94e454a6a4f3c8` (Codespaces IP allowlist - controls access to agent ports 9000/9001)

### Deploying the Calculator Agent

SSH into the EC2 instance and run:

```bash
# Clone the repo
git clone <repo-url> /home/ubuntu/strands_a2a
cd /home/ubuntu/strands_a2a

# Install dependencies system-wide
pip3 install -r agents/calculator/requirements.txt

# Install and start the systemd service
sudo cp agents/calculator/deploy/strands-calculator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable strands-calculator
sudo systemctl start strands-calculator

# Verify it started
sudo systemctl status strands-calculator
```

The service fetches secrets automatically from Secrets Manager on startup. The agent will be available on port 9000.

### Deploying the Clock Agent

SSH into a separate EC2 instance and run:

```bash
# Clone the repo
git clone <repo-url> /home/ubuntu/strands_a2a
cd /home/ubuntu/strands_a2a

# Install dependencies system-wide
pip3 install -r agents/clock/requirements.txt

# Install and start the systemd service
sudo cp agents/clock/deploy/strands-clock.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable strands-clock
sudo systemctl start strands-clock

# Verify it started
sudo systemctl status strands-clock
```

The agent will be available on port 9001.

### Service Management (on EC2)

```bash
# View live logs
sudo journalctl -u strands-calculator.service -f
sudo journalctl -u strands-clock.service -f

# Restart
sudo systemctl restart strands-calculator.service
sudo systemctl restart strands-clock.service

# Update code and restart
cd /home/ubuntu/strands_a2a
git pull
pip3 install -r agents/calculator/requirements.txt  # or clock
sudo systemctl restart strands-calculator.service  # or strands-clock
```

### Changing the Port

Edit the `AGENT_PORT` line in the systemd service file before copying it:

```ini
# agents/calculator/deploy/strands-calculator.service
Environment="AGENT_PORT=9000"  # change this
```

## Architecture

### Independent Agent Design

Each agent directory (`agents/calculator/`, `agents/clock/`) is fully self-contained:
- Its own `requirements.txt` (no shared install needed)
- Its own `start_server.sh` that handles secrets, git pull, and starting the agent
- Its own systemd service file
- No dependency on the other agent at runtime

The `src/server.py` launcher is for local development only. In production each EC2 instance runs one agent process directly.

### Authentication

- All endpoints require `Authorization: Bearer <API_PASSWORD>`
- **Exception:** `/.well-known/agent-card.json` is always public (no auth required)

### Agent Tools

**Calculator Agent** uses `strands_tools.calculator`:
- Arithmetic: addition, subtraction, multiplication, division
- Powered by SymPy for accurate evaluation

**Clock Agent** uses `strands_tools.current_time`:
- Returns current time in ISO 8601 format
- Accepts any IANA timezone string (e.g. `UTC`, `US/Pacific`, `Asia/Tokyo`)
- Falls back to `UTC` if no timezone specified

## Solace Agent Mesh Integration

Connect your agents to the Solace Agent Mesh for broader agent ecosystems:

```yaml
# Example configuration (see examples/sample_proxy.yaml)
proxied_agents:
  - name: "StrandsCalculator"
    url: "http://calculator-ec2-host:9000"
  - name: "StrandsClock"
    url: "http://clock-ec2-host:9001"
```

1. Install [Solace Agent Mesh](https://github.com/SolaceLabs/solace-agent-mesh)
2. Place config in `configs/agents/` directory
3. Start the mesh to connect your agents

## Dependencies

- **strands-agents[a2a,litellm]** - Core Strands framework
- **strands-agents-tools** - Built-in tools (calculator, current_time)
- **a2a-sdk[sql]** - A2A protocol implementation
- **bedrock-agentcore** - AWS Bedrock integration (top-level only)

## License

See repository license file.

## Contributing

Contributions are welcome. Follow the existing code structure and conventions outlined in [CLAUDE.md](CLAUDE.md).
