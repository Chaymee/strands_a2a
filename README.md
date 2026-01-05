# Strands A2A Server

A simple implementation of Strands agents exposed as an A2A (Agent-to-Agent) server.

## Overview

This project sets up a basic A2A server using the Strands framework. It creates a Calculator Agent that can perform basic arithmetic operations using the [Strands calculator tool](https://github.com/strands-agents/tools/tree/main/src/strands_tools) and exposes it through an A2A server interface, allowing other agents to communicate with it.

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

## Running the A2A Server

### Set API Password (Optional)

Set the API password for authenticating API calls:

```bash
export API_PASSWORD="your_secure_password_here"
```

If not set, the server will use `default_password` as the default password.

### Start the Server

To start the A2A server, run:

```bash
python server.py
```

The server will start and expose the Calculator Agent through the A2A protocol. By default, it will listen on `localhost:9000`.

### Accessing Agent Cards

To access the well-known agents cards in this server, navigate to:

```
http://host:port/.well-known/agent-card.json
```

For example, if running locally on the default port:

```
http://localhost:9000/.well-known/agent-card.json
```

This endpoint provides standardized metadata about the agent capabilities according to the A2A protocol.

### Executing the agent

The server requires password authentication for API calls. Set the `API_PASSWORD` environment variable before starting the server (defaults to `default_password` if not set).

Run the following from terminal with authentication:
```
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
          "text": "What is 10 * 11? Give me the answer and shaksperean style. The answer should be one short sentence"
        }
      ],
      "messageId": "12345678-1234-1234-1234-123456789012"
    }
  }
}' | jq .
```

**Note:** The `/.well-known/agent-card.json` endpoint does NOT require authentication and can be accessed without the Authorization header.

## Project Structure

- `server.py`: Main script that creates and starts the A2A server with a Calculator Agent
- `requirements.txt`: List of Python dependencies required for the project

## How It Works

The server.py file:
1. Creates a Strands agent with a calculator tool
2. Initializes an A2A server with this agent
3. Starts the server to listen for incoming requests

Other agents can now connect to this server and utilize the calculator functionality through the A2A protocol.

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