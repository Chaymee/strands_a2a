"""
Calculator Agent
Performs basic arithmetic operations via the A2A protocol.
Default port: 9000
"""

import os
from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.models.litellm import LiteLLMModel
from strands_tools.calculator import calculator
from fastapi import Request
from fastapi.responses import JSONResponse
import uvicorn

PORT = 9000
NAME = "Calculator Agent"


def create_llm_model():
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


def run(port: int = PORT):
    api_password = os.getenv("API_PASSWORD")
    host = os.getenv("API_HOST", "0.0.0.0")
    public_url = os.getenv("PUBLIC_URL")

    print(f"[{NAME}] HOST={host}")
    print(f"[{NAME}] PUBLIC_URL={public_url}")

    if not api_password:
        raise ValueError("API_PASSWORD environment variable is not set.")

    llm_model = create_llm_model()

    agent = Agent(
        name=NAME,
        description="A calculator agent that can perform basic arithmetic operations.",
        model=llm_model,
        tools=[calculator],
        callback_handler=None,
    )

    http_url = f"{public_url}:{port}" if public_url else None
    a2a_server = A2AServer(agent=agent, host=host, port=port, http_url=http_url)
    app = a2a_server.to_fastapi_app()

    @app.middleware("http")
    async def authenticate_requests(request: Request, call_next):
        if request.url.path == "/.well-known/agent-card.json":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {api_password}":
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid or missing API password"},
            )

        return await call_next(request)

    print(f"[{NAME}] Starting on http://{host}:{port}")
    print(f"[{NAME}] Agent card: http://{host}:{port}/.well-known/agent-card.json")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
