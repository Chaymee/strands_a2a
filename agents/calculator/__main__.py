import os
from agents.calculator.agent import run, PORT

run(port=int(os.environ.get("AGENT_PORT", PORT)))
