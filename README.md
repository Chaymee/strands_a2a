# Strands A2A Server

A simple implementation of Strands agents exposed as an A2A (Agent-to-Agent) server.

## Overview

This project sets up A2A servers using the Strands framework. It includes two agents:

1. **Calculator Agent** - Performs basic arithmetic operations using the [Strands calculator tool](https://github.com/strands-agents/tools/tree/main/src/strands_tools)
2. **Factor Agent** - Extracts numbers from input text and returns all possible factors of that number

Both agents are exposed through an A2A server interface, allowing other agents to communicate with them.

## Three Ways to Run the Agents

This project provides **three separate executable files**:

1. **`server.py`** - Multi-agent server that runs BOTH Calculator and Factor agents together in parallel processes
2. **`calculator.py`** - Standalone server that runs ONLY the Calculator Agent
3. **`factor.py`** - Standalone server that runs ONLY the Factor Agent

**Note:** `server.py` does NOT call `calculator.py` or `factor.py`. Instead, it contains its own implementation of both agents and runs them in parallel. The individual files (`calculator.py` and `factor.py`) are standalone alternatives for running each agent separately.

## Prerequisites

- Python 3.10+
- AWS account with Bedrock LLM model enabled
- AWS_ACCESS_KEY
- AWS_SECRET_ACCESS_KEY

### If you are using aws sso
Sign in with `aws sso login --profile<profile-name>`
then export your profile `export AWS_PROFILE=<profile-name>`
to be able to access 

## Setup Instructions

### 1. Create and Activate a Python Virtual Environment

#### On macOS/Linux:
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate
```

#### On Windows:
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate
```

### 2. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

This will install:
- strands-agents[a2a] (version 1.3.0)
- strands-agents-tools (version 0.2.0)
- a2a-sdk[sql] (version 0.3.0)

## Running the A2A Servers

### Set API Password (Required)

Set the API password for authenticating API calls:

```bash
export API_PASSWORD="your_secure_password_here"
```

This password is required for both agents.

### Start the Servers

**Option 1: Start Both Agents Together (Recommended)**

Run both agents simultaneously using the main server:
```bash
python server.py
```

This will start:
- Calculator Agent on port 9000
- Factor Agent on port 9001

**Option 2: Start Agents Individually**

**Calculator Agent** (default port: 9000):
```bash
python calculator.py
```

**Factor Agent** (default port: 9001):
```bash
python factor.py
```

You can specify custom ports using the `-p` flag:
```bash
python calculator.py -p 8000
python factor.py -p 8001
```

All servers expose their respective agents through the A2A protocol.

### Accessing Agent Cards

To access the well-known agent cards, navigate to:

```
http://host:port/.well-known/agent-card.json
```

For example, if running locally on the default ports:

**Calculator Agent:**
```
http://localhost:9000/.well-known/agent-card.json
```

**Factor Agent:**
```
http://localhost:9001/.well-known/agent-card.json
```

This endpoint provides standardized metadata about each agent's capabilities according to the A2A protocol.

### Executing the Agents

Both servers require password authentication for API calls. Set the `API_PASSWORD` environment variable before starting the servers.

#### Calculator Agent Example

Run the following from terminal with authentication:
```bash
curl -X POST http://localhost:9000 \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_secure_password_here" \
-d '{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "What is 10 * 11? Give me the answer in Shakespearean style. The answer should be one short sentence"
        }
      ],
      "messageId": "12345678-1234-1234-1234-123456789012"
    }
  }
}' | jq .
```

#### Factor Agent Example

Run the following to find factors of a number:
```bash
curl -X POST http://localhost:9001 \
-H "Content-Type: application/json" \
-H "Authorization: Bearer your_secure_password_here" \
-d '{
  "jsonrpc": "2.0",
  "id": "req-002",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "What are the factors of 24?"
        }
      ],
      "messageId": "87654321-4321-4321-4321-210987654321"
    }
  }
}' | jq .
```

**Note:** The `/.well-known/agent-card.json` endpoint does NOT require authentication and can be accessed without the Authorization header.

## Project Structure

### Three Executable Files:

1. **`server.py`** - Multi-agent server (runs BOTH agents together)
   - Starts Calculator Agent on port 9000
   - Starts Factor Agent on port 9001
   - Runs both agents in parallel processes using Python's multiprocessing
   - Contains its own implementation of both agents (does NOT import from calculator.py or factor.py)

2. **`calculator.py`** - Standalone Calculator Agent server
   - Runs ONLY the Calculator Agent
   - Default port: 9000 (configurable with `-p` flag)
   - Independent executable for running calculator functionality alone

3. **`factor.py`** - Standalone Factor Agent server
   - Runs ONLY the Factor Agent
   - Default port: 9001 (configurable with `-p` flag)
   - Independent executable for running factor functionality alone

### Deployment Files:

- `start_server.sh`: Wrapper script that fetches secrets from AWS Secrets Manager and starts the server
- `deployment/`: Directory containing AWS deployment configuration
  - `DEPLOYMENT.md`: Complete guide for deploying to AWS EC2
  - `setup-aws.sh`: Automated script to create AWS resources (IAM roles, policies, secrets)
  - `strands-a2a.service`: systemd service file for auto-start on boot
  - `ec2-iam-policy.json`: IAM policy for EC2 instance to access secrets

### Other Files:

- `requirements.txt`: List of Python dependencies required for the project

## How It Works

### server.py (Multi-Agent Server - Combination of Both Agents):
1. Contains its own implementation of both the Calculator and Factor agents
2. Uses Python's `multiprocessing` module to run both agents in parallel
3. Starts Calculator Agent on port 9000
4. Starts Factor Agent on port 9001
5. Handles graceful shutdown with Ctrl+C
6. **Does NOT call or import from calculator.py or factor.py** - it's a self-contained implementation

### Individual Agent Files (calculator.py and factor.py - Standalone):
1. Define tool function(s) using the `@tool` decorator
2. Create a Strands agent with the tool(s) and LiteLLM model configuration
3. Initialize an A2A server with the agent
4. Add authentication middleware
5. Start the server to listen for incoming requests
6. Can be run independently without server.py

Other agents can now connect to these servers and utilize their functionality through the A2A protocol.

## AWS EC2 Deployment

To deploy this application to AWS EC2 with automatic startup and secure credential management:

### Quick Start

1. **Run the automated setup script:**
   ```bash
   cd deployment
   ./setup-aws.sh
   ```
   This will create all necessary AWS resources (Secrets Manager secret, IAM roles, policies, etc.)

2. **Follow the deployment guide:**
   See [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md) for complete step-by-step instructions.

### Key Features of AWS Deployment

- **Automatic startup on boot** using systemd
- **Secure credential storage** with AWS Secrets Manager (no hardcoded passwords)
- **IAM role-based access** for secure secret retrieval
- **Service monitoring** with systemd and CloudWatch integration
- **Easy updates** - pull code changes and restart service

The deployment uses:
- `start_server.sh` - Fetches secrets and starts the server
- `deployment/strands-a2a.service` - systemd service for auto-start
- `deployment/setup-aws.sh` - Automated AWS resource creation

For detailed instructions, see [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md).

## Connecting with Solace Agent Mesh

You can connect this Strands A2A server to the [Solace Agent Mesh](https://github.com/SolaceLabs/solace-agent-mesh) to enable communication with other agents on the mesh. This allows your Strands agent to participate in a broader ecosystem of agents.

### Sample Proxy Configuration

A sample configuration file (`sample_proxy.yaml`) is provided to demonstrate how to configure the Solace Agent Mesh A2A proxy to connect to this Strands A2A server:

```yaml
# --- List of Downstream Agents to Proxy ---
proxied_agents:
  # Example: Connecting to the Strands Calculator Agent
  - name: "StrandsCalculator" # The name this agent will have on the Solace mesh
    url: "http://0.0.0.0:9000" # The real HTTP endpoint of the agent
```

### Setting Up Solace Agent Mesh

To set up and configure Solace Agent Mesh:

1. Follow the installation and initialization instructions in the [Solace Agent Mesh documentation](https://github.com/SolaceLabs/solace-agent-mesh).

1. Configure the A2A proxy using the sample configuration provided above, adjusting the URL to match your Strands A2A server's address. Note, you can place this yamle file under `configs/agents`

1. Start the Solace Agent Mesh with your configuration to connect your Strands agent to the mesh.

This integration enables your Strands Calculator Agent to communicate with other agents on the Solace event mesh, expanding its capabilities and reach.