from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands.models.litellm import LiteLLMModel
import importlib.metadata
import argparse
import os
import re
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn


@tool
def find_factors(input_text: str) -> dict:
    """
    Extract a number from the input text and return all possible factors of that number.

    This tool searches for numbers in the input text, extracts the first number found,
    and calculates all factors (divisors) of that number.

    Args:
        input_text: The input text containing a number to factorize.

    Returns:
        A dictionary with status and content containing the factors.
    """
    # Extract numbers from the input text
    numbers = re.findall(r'\d+', input_text)

    if not numbers:
        return {
            "status": "error",
            "content": [{"text": "No number found in the input text."}]
        }

    # Get the first number found
    number = int(numbers[0])

    if number <= 0:
        return {
            "status": "error",
            "content": [{"text": "Please provide a positive integer greater than 0."}]
        }

    # Find all factors
    factors = []
    for i in range(1, number + 1):
        if number % i == 0:
            factors.append(i)

    # Format the result
    factors_str = ", ".join(str(f) for f in factors)
    result_text = f"The factors of {number} are: {factors_str}"

    return {
        "status": "success",
        "content": [{"text": result_text}]
    }


# Parse command line arguments
parser = argparse.ArgumentParser(description='Start A2A Server with Factor Agent')
parser.add_argument('-p', '--port', type=int, default=9001, help='Port number (default: 9001)')
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

# Create a Strands agent with factor tool and custom LiteLLM model
strands_agent = Agent(
    name="Factor Agent",
    description="A factor agent that extracts numbers from input and returns all possible factors.",
    model=llm_model,
    tools=[find_factors],
    callback_handler=None,
)

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
