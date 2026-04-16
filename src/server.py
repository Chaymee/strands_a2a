"""
Multi-Agent A2A Server
Launches the Calculator Agent (port 9000) and Clock Agent (port 9001) in separate processes.
Use this for local development only. For production, deploy each agent independently.
"""

import importlib.metadata
import multiprocessing
import sys
import time

from agents.calculator.agent import run as run_calculator
from agents.clock.agent import run as run_clock


def main():
    try:
        strands_version = importlib.metadata.version("strands-agents")
        a2a_version = importlib.metadata.version("a2a-sdk")
        print(f"Strands version: {strands_version}")
        print(f"A2A SDK version: {a2a_version}")
    except Exception as e:
        print(f"Could not determine version information: {e}")

    print("\n=== Starting Multi-Agent A2A Server (local dev) ===")
    print("API authentication enabled. Set API_PASSWORD to change the password.\n")

    calculator_process = multiprocessing.Process(target=run_calculator, args=(9000,))
    clock_process = multiprocessing.Process(target=run_clock, args=(9001,))

    calculator_process.start()
    time.sleep(1)
    clock_process.start()

    try:
        calculator_process.join()
        clock_process.join()
    except KeyboardInterrupt:
        print("\n\nShutting down agents...")
        calculator_process.terminate()
        clock_process.terminate()
        calculator_process.join()
        clock_process.join()
        print("All agents stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
