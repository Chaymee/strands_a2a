from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.models.litellm import LiteLLMModel
from strands_tools.calculator import calculator
import importlib.metadata
import argparse
import os
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from strands.models.litellm import LiteLLMModel


# Parse command line arguments
parser = argparse.ArgumentParser(description='Start A2A Server with Calculator Agent')
parser.add_argument('-p', '--port', type=int, default=9000, help='Port number (default: 9000)')
args = parser.parse_args()

# Get API password from environment variable
API_PASSWORD = os.getenv('API_PASSWORD')
HOST = os.getenv('API_HOST', '0.0.0.0')
print(f"API authentication enabled. Set API_PASSWORD environment variable to change the password.")
if not API_PASSWORD:
    raise ValueError("API_PASSWORD environment variable is not set. Please set it to enable authentication.")


# Configure LiteLLM with custom endpoint
litellm_endpoint = os.environ.get("LLM_SERVICE_ENDPOINT", "https://lite-llm.mymaas.net")
litellm_api_key = os.environ.get("LLM_SERVICE_API_KEY")

if not litellm_api_key:
    raise ValueError("LLM_SERVICE_API_KEY environment variable is required")

# Create LiteLLM model with custom endpoint configuration
llm_model = LiteLLMModel(
    client_args={
        "api_base": litellm_endpoint,
        "api_key": litellm_api_key,
    },
    model_id="openai/vertex-claude-4-5-sonnet",
)

# Create a Strands agent with calculator tool and custom LiteLLM model
strands_agent = Agent(
    name="Calculator Agent",
    description="A calculator agent that can perform basic arithmetic operations.",
    model=llm_model,
    tools=[calculator],
    callback_handler=None,
)

# # Create a Strands agent with calculator tool
# # Using Amazon Bedrock default model provider and Claude 3.7 Sonnet as default FM
# strands_agent = Agent(
#     name="Calculator Agent",
#     description="A calculator agent that can perform basic arithmetic operations.",
#     tools=[calculator],
#     callback_handler=None,
# )


# Get version information
try:
    strands_version = importlib.metadata.version("strands-agents")
    a2a_version = importlib.metadata.version("a2a-sdk")
    print(f"Strands version: {strands_version}")
    print(f"A2A SDK version: {a2a_version}")
except Exception as e:
    print(f"Could not determine version information: {e}")

# Create A2A server
a2a_server = A2AServer(agent=strands_agent, host=HOST, port=args.port)

# Get the FastAPI app
app = a2a_server.to_fastapi_app()

# Add authentication middleware
@app.middleware("http")
async def authenticate_requests(request: Request, call_next):
    # Skip authentication for agent card endpoint
    if request.url.path == "/.well-known/agent-card.json":
        return await call_next(request)

    # Check for Authorization header
    auth_header = request.headers.get("Authorization")

    # Validate token
    if auth_header != f"Bearer {API_PASSWORD}":
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "message": "Invalid or missing API password"}
        )

    # Continue to the actual endpoint
    return await call_next(request)

# Start the server
print(f"Starting A2A Server on http://{HOST}:{args.port}")
print(f"Navigate to http://{HOST}:{args.port}/.well-known/agent-card.json to get agent card")
uvicorn.run(app, host="0.0.0.0", port=args.port)
