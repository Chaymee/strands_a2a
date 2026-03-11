# Strands A2A Server

A multi-agent server implementation using the Strands framework, exposing AI agents via the A2A (Agent-to-Agent) protocol.

## Overview

This project provides two intelligent agents accessible through a standardized A2A interface:

1. **Calculator Agent** (port 9000) - Performs arithmetic operations using the [Strands calculator tool](https://github.com/strands-agents/tools)
2. **Factor Agent** (port 9001) - Extracts numbers and returns their prime factors

Both agents run in parallel processes and are secured with Bearer token authentication.

## Quick Start

### Local Development

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export API_PASSWORD="your_secure_password"
export LLM_SERVICE_API_KEY="your_litellm_api_key"

# 4. Run the server
python -m src.server
```

The server will start both agents:
- Calculator Agent: http://localhost:9000
- Factor Agent: http://localhost:9001

### AWS Deployment

```bash
# Quick deploy to AWS EC2
cd deploy
./setup-aws.sh  # Creates all AWS resources

# See deploy/README.md for detailed instructions
```

## Project Structure

```
strands_a2a/
├── src/
│   └── server.py              # Multi-agent server implementation
├── tests/
│   ├── load_test.py           # Load testing script
│   └── run_load_test.sh       # Test wrapper
├── deploy/
│   ├── README.md              # AWS deployment guide
│   ├── start_server.sh        # Production startup script
│   ├── setup-aws.sh           # AWS resource automation
│   ├── strands-a2a.service    # systemd service
│   └── ec2-iam-policy.json    # IAM policy
└── examples/
    └── sample_proxy.yaml      # Solace mesh config
```

## Usage

### Testing the Agents

**Agent Card (no auth required):**
```bash
curl http://localhost:9000/.well-known/agent-card.json
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

**Factor Agent:**
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
        "parts": [{"kind": "text", "text": "What are the factors of 24?"}],
        "messageId": "87654321-4321-4321-4321-210987654321"
      }
    }
  }'
```

### Load Testing

```bash
# Quick smoke test (10 users)
./tests/run_load_test.sh light

# Test with 100 concurrent users
./tests/run_load_test.sh 100

# Test factor agent with 250 users
./tests/run_load_test.sh -u http://localhost:9001 -a factor 250

# Custom test with output file
./tests/run_load_test.sh --users 150 --requests 10 -o results.json custom
```

## Configuration

### Environment Variables

**Required:**
- `API_PASSWORD` - Bearer token for API authentication
- `LLM_SERVICE_API_KEY` - API key for LiteLLM service

**Optional:**
- `LLM_SERVICE_ENDPOINT` - LiteLLM endpoint (default: "https://lite-llm.mymaas.net")
- `API_HOST` - Bind address (default: "0.0.0.0")
- `PUBLIC_URL` - Public URL for agent cards (auto-detected on EC2)
- `AWS_REGION` - AWS region for deployments (default: "us-east-1")

### AWS Secrets Manager

For AWS deployments, credentials are stored in AWS Secrets Manager at `strands-a2a/credentials`:

```json
{
  "API_PASSWORD": "your_password",
  "LLM_SERVICE_API_KEY": "your_key",
  "LLM_SERVICE_ENDPOINT": "https://lite-llm.mymaas.net"
}
```

## Architecture

### Multi-Agent Server

The `src/server.py` file contains a self-contained implementation that:
- Runs both agents in parallel using Python multiprocessing
- Each agent runs in its own process for true parallelism
- Handles graceful shutdown with Ctrl+C
- Configures LiteLLM with custom endpoints
- Implements FastAPI middleware for Bearer token authentication

### Authentication

- All endpoints require Bearer token authentication via `Authorization: Bearer <token>` header
- **Exception:** `/.well-known/agent-card.json` is public (no auth required)
- Token must match the `API_PASSWORD` environment variable

### Agent Tools

**Calculator Agent:**
- Uses the Strands calculator tool for arithmetic operations
- Supports addition, subtraction, multiplication, division

**Factor Agent:**
- Custom tool to find all factors of a number
- Extracts numbers from natural language input
- Returns factors in a structured format

## AWS Deployment

The project includes complete AWS infrastructure:

### Features
- **Automatic startup** via systemd service
- **Secure credentials** with AWS Secrets Manager
- **IAM role-based access** (no hardcoded secrets)
- **Auto-pull latest code** on server start
- **Service monitoring** with journald logs

### Quick Deploy

```bash
cd deploy
./setup-aws.sh
```

This creates:
- AWS Secrets Manager secret
- IAM policy for secret access
- IAM role and instance profile
- Guided EC2 instance setup

### Service Management (on EC2)

```bash
# View logs
sudo journalctl -u strands-a2a.service -f

# Restart service
sudo systemctl restart strands-a2a.service

# Check status
sudo systemctl status strands-a2a.service

# Update and restart
cd /home/ubuntu/strands_a2a
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart strands-a2a.service
```

See [deploy/README.md](deploy/README.md) for detailed deployment instructions.

## Solace Agent Mesh Integration

Connect your agents to the Solace Agent Mesh for broader agent ecosystems:

```yaml
# Example configuration (see examples/sample_proxy.yaml)
proxied_agents:
  - name: "StrandsCalculator"
    url: "http://localhost:9000"
  - name: "StrandsFactor"
    url: "http://localhost:9001"
```

1. Install [Solace Agent Mesh](https://github.com/SolaceLabs/solace-agent-mesh)
2. Place config in `configs/agents/` directory
3. Start the mesh to connect your agents

## Dependencies

- **strands-agents[a2a,litellm]** (1.3.0+) - Core Strands framework
- **strands-agents-tools** (0.2.0+) - Calculator tool
- **a2a-sdk[sql]** (0.3.0+) - A2A protocol implementation
- **bedrock-agentcore** - AWS Bedrock integration

## License

See repository license file.

## Contributing

Contributions are welcome! Please follow the existing code structure and conventions outlined in [CLAUDE.md](CLAUDE.md).
