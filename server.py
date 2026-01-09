"""
Multi-Agent A2A Server
Starts both Calculator and Factor agents in parallel processes.
"""

import multiprocessing
import os
import sys
import time
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands.models.litellm import LiteLLMModel
from strands_tools.calculator import calculator
import importlib.metadata
import re
from fastapi import Request
from fastapi.responses import JSONResponse
import uvicorn


def create_llm_model():
    """Create and configure the LiteLLM model."""
    litellm_endpoint = os.environ.get("LLM_SERVICE_ENDPOINT", "https://lite-llm.mymaas.net")
    litellm_api_key = os.environ.get("LLM_SERVICE_API_KEY")

    if not litellm_api_key:
        raise ValueError("LLM_SERVICE_API_KEY environment variable is required")

    return LiteLLMModel(
        client_args={
            "api_base": litellm_endpoint,
            "api_key": litellm_api_key,
        },
        model_id="openai/vertex-claude-4-5-sonnet",
    )


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


def start_calculator_agent(port=9000):
    """Start the Calculator Agent on the specified port."""
    # Get API password from environment variable
    API_PASSWORD = os.getenv('API_PASSWORD')
    HOST = os.getenv('API_HOST', '0.0.0.0')

    if not API_PASSWORD:
        raise ValueError("API_PASSWORD environment variable is not set. Please set it to enable authentication.")

    # Create LiteLLM model
    llm_model = create_llm_model()

    # Create Calculator Agent
    calculator_agent = Agent(
        name="Calculator Agent",
        description="A calculator agent that can perform basic arithmetic operations.",
        model=llm_model,
        tools=[calculator],
        callback_handler=None,
    )

    # Create A2A server
    a2a_server = A2AServer(agent=calculator_agent, host=HOST, port=port)
    app = a2a_server.to_fastapi_app()

    # Add authentication middleware
    @app.middleware("http")
    async def authenticate_requests(request: Request, call_next):
        if request.url.path == "/.well-known/agent-card.json":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {API_PASSWORD}":
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid or missing API password"}
            )

        return await call_next(request)

    # Start the server
    print(f"[Calculator Agent] Starting on http://{HOST}:{port}")
    print(f"[Calculator Agent] Agent card: http://{HOST}:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)


def start_factor_agent(port=9001):
    """Start the Factor Agent on the specified port."""
    # Get API password from environment variable
    API_PASSWORD = os.getenv('API_PASSWORD')
    HOST = os.getenv('API_HOST', '0.0.0.0')

    if not API_PASSWORD:
        raise ValueError("API_PASSWORD environment variable is not set. Please set it to enable authentication.")

    # Create LiteLLM model
    llm_model = create_llm_model()

    # Create Factor Agent
    factor_agent = Agent(
        name="Factor Agent",
        description="A factor agent that extracts numbers from input and returns all possible factors.",
        model=llm_model,
        tools=[find_factors],
        callback_handler=None,
    )

    # Create A2A server
    a2a_server = A2AServer(agent=factor_agent, host=HOST, port=port)
    app = a2a_server.to_fastapi_app()

    # Add authentication middleware
    @app.middleware("http")
    async def authenticate_requests(request: Request, call_next):
        if request.url.path == "/.well-known/agent-card.json":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {API_PASSWORD}":
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid or missing API password"}
            )

        return await call_next(request)

    # Start the server
    print(f"[Factor Agent] Starting on http://{HOST}:{port}")
    print(f"[Factor Agent] Agent card: http://{HOST}:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    """Main function to start both agents in parallel."""
    # Get version information
    try:
        strands_version = importlib.metadata.version("strands-agents")
        a2a_version = importlib.metadata.version("a2a-sdk")
        print(f"Strands version: {strands_version}")
        print(f"A2A SDK version: {a2a_version}")
    except Exception as e:
        print(f"Could not determine version information: {e}")

    print("\n=== Starting Multi-Agent A2A Server ===")
    print("API authentication enabled. Set API_PASSWORD environment variable to change the password.\n")

    # Create processes for each agent
    calculator_process = multiprocessing.Process(target=start_calculator_agent, args=(9000,))
    factor_process = multiprocessing.Process(target=start_factor_agent, args=(9001,))

    # Start both processes
    calculator_process.start()
    time.sleep(1)  # Small delay to stagger startup
    factor_process.start()

    try:
        # Wait for both processes
        calculator_process.join()
        factor_process.join()
    except KeyboardInterrupt:
        print("\n\nShutting down agents...")
        calculator_process.terminate()
        factor_process.terminate()
        calculator_process.join()
        factor_process.join()
        print("All agents stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
