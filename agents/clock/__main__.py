import os
from agents.clock.agent import run, PORT

run(port=int(os.environ.get("AGENT_PORT", PORT)))
