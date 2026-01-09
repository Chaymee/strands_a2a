# Strands A2A Server

A simple implementation of Strands agents exposed as an A2A (Agent-to-Agent) server.

## Overview

This project sets up A2A servers using the Strands framework. It includes two agents:

1. **Calculator Agent** (`calculator.py`) - Performs basic arithmetic operations using the [Strands calculator tool](https://github.com/strands-agents/tools/tree/main/src/strands_tools)
2. **Factor Agent** (`factor.py`) - Extracts numbers from input text and returns all possible factors of that number

Both agents are exposed through an A2A server interface, allowing other agents to communicate with them.

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

- `server.py`: **Main server** - Starts both Calculator and Factor agents in parallel processes
- `calculator.py`: Standalone A2A server with a Calculator Agent that performs arithmetic operations
- `factor.py`: Standalone A2A server with a Factor Agent that finds all factors of a number
- `requirements.txt`: List of Python dependencies required for the project

## How It Works

**server.py** (Multi-Agent Server):
1. Uses Python's `multiprocessing` module to run both agents in parallel
2. Starts Calculator Agent on port 9000
3. Starts Factor Agent on port 9001
4. Handles graceful shutdown with Ctrl+C

**Individual Agent Files** (calculator.py, factor.py):
1. Define tool function(s) using the `@tool` decorator
2. Create a Strands agent with the tool(s) and LiteLLM model configuration
3. Initialize an A2A server with the agent
4. Add authentication middleware
5. Start the server to listen for incoming requests

Other agents can now connect to these servers and utilize their functionality through the A2A protocol.

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