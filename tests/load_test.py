#!/usr/bin/env python3
"""
Load testing script for Strands A2A agents.

Tests both Calculator and Factor agents with configurable concurrent users.
Provides detailed statistics on response times, success rates, and throughput.

Usage:
    python load_test.py --url https://your-agent-url.com --users 100
    python load_test.py --url https://your-agent-url.com --users 250 --agent factor
    python load_test.py --help
"""

import argparse
import asyncio
import json
import statistics
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp


class LoadTester:
    """Load testing framework for A2A agents."""

    def __init__(
        self,
        base_url: str,
        api_password: str,
        agent_type: str = "calculator",
        num_users: int = 100,
        requests_per_user: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_password = api_password
        self.agent_type = agent_type
        self.num_users = num_users
        self.requests_per_user = requests_per_user

        # Results tracking
        self.results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    def get_test_messages(self) -> List[str]:
        """Get test messages based on agent type."""
        if self.agent_type == "calculator":
            return [
                "What is 10 + 5?",
                "Calculate 25 * 4",
                "What is 100 - 37?",
                "Divide 144 by 12",
                "What is 7 * 8?",
                "Calculate 1000 + 234",
                "What is 50 / 2?",
                "Calculate 15 * 15",
            ]
        elif self.agent_type == "factor":
            return [
                "Extract numbers and find factors from: The number 12 is interesting",
                "What are the factors of 24?",
                "Extract numbers: I have 36 apples",
                "Find factors in: The answer is 48",
                "Extract and factor: There are 60 students",
                "What are factors of 100?",
                "Extract from: We need 72 units",
                "Find factors in: The total is 84",
            ]
        else:
            raise ValueError(f"Unknown agent type: {self.agent_type}")

    async def send_request(
        self, session: aiohttp.ClientSession, message: str, user_id: int, request_num: int
    ) -> Dict:
        """Send a single A2A request to the agent."""
        start_time = time.time()

        payload = {
            "jsonrpc": "2.0",
            "id": f"req-{user_id}-{request_num}",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": str(uuid.uuid4()),
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_password}",
        }

        try:
            async with session.post(
                self.base_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = time.time() - start_time
                status = response.status

                try:
                    response_data = await response.json()
                except Exception:
                    response_data = await response.text()

                return {
                    "success": status == 200,
                    "status_code": status,
                    "response_time": response_time,
                    "response_data": response_data,
                    "error": None if status == 200 else f"HTTP {status}",
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "status_code": None,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": "Request timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time": time.time() - start_time,
                "response_data": None,
                "error": str(e),
            }

    async def simulate_user(
        self, session: aiohttp.ClientSession, user_id: int, messages: List[str]
    ):
        """Simulate a single user making multiple requests."""
        import random

        for i in range(self.requests_per_user):
            message = random.choice(messages)
            result = await self.send_request(session, message, user_id, i)

            # Track results
            self.results["total_requests"] += 1
            if result["success"]:
                self.results["successful_requests"] += 1
            else:
                self.results["failed_requests"] += 1
                self.results["errors"].append(
                    {
                        "user_id": user_id,
                        "request_num": i,
                        "error": result["error"],
                        "status_code": result["status_code"],
                    }
                )

            self.results["response_times"].append(result["response_time"])

            # Small delay between requests from same user
            await asyncio.sleep(0.1)

    async def run_load_test(self):
        """Execute the load test with configured number of users."""
        print(f"\n{'='*70}")
        print(f"Strands A2A Load Test")
        print(f"{'='*70}")
        print(f"Target URL: {self.base_url}")
        print(f"Agent Type: {self.agent_type}")
        print(f"Concurrent Users: {self.num_users}")
        print(f"Requests per User: {self.requests_per_user}")
        print(f"Total Requests: {self.num_users * self.requests_per_user}")
        print(f"{'='*70}\n")

        # Test agent card endpoint (no auth)
        print("Testing agent card endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/.well-known/agent-card.json"
                ) as response:
                    if response.status == 200:
                        card_data = await response.json()
                        print(f"✓ Agent card retrieved: {card_data.get('name', 'Unknown')}")
                    else:
                        print(f"✗ Agent card failed: HTTP {response.status}")
        except Exception as e:
            print(f"✗ Agent card error: {e}")

        print("\nStarting load test...\n")

        messages = self.get_test_messages()
        self.results["start_time"] = datetime.now()

        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=self.num_users, limit_per_host=self.num_users)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create tasks for all users
            tasks = [
                self.simulate_user(session, user_id, messages)
                for user_id in range(self.num_users)
            ]

            # Run all users concurrently
            await asyncio.gather(*tasks)

        self.results["end_time"] = datetime.now()

    def print_results(self):
        """Print detailed test results and statistics."""
        print(f"\n{'='*70}")
        print(f"Load Test Results")
        print(f"{'='*70}\n")

        # Overall metrics
        duration = (self.results["end_time"] - self.results["start_time"]).total_seconds()
        success_rate = (
            (self.results["successful_requests"] / self.results["total_requests"] * 100)
            if self.results["total_requests"] > 0
            else 0
        )
        throughput = self.results["total_requests"] / duration if duration > 0 else 0

        print(f"Duration: {duration:.2f} seconds")
        print(f"Total Requests: {self.results['total_requests']}")
        print(f"Successful: {self.results['successful_requests']} ({success_rate:.1f}%)")
        print(f"Failed: {self.results['failed_requests']}")
        print(f"Throughput: {throughput:.2f} requests/second")

        # Response time statistics
        if self.results["response_times"]:
            print(f"\nResponse Times:")
            print(f"  Min: {min(self.results['response_times']):.3f}s")
            print(f"  Max: {max(self.results['response_times']):.3f}s")
            print(f"  Mean: {statistics.mean(self.results['response_times']):.3f}s")
            print(f"  Median: {statistics.median(self.results['response_times']):.3f}s")
            if len(self.results["response_times"]) > 1:
                print(
                    f"  Std Dev: {statistics.stdev(self.results['response_times']):.3f}s"
                )

            # Percentiles
            sorted_times = sorted(self.results["response_times"])
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            print(f"  95th Percentile: {sorted_times[p95_idx]:.3f}s")
            print(f"  99th Percentile: {sorted_times[p99_idx]:.3f}s")

        # Error details
        if self.results["errors"]:
            print(f"\nErrors ({len(self.results['errors'])} total):")
            error_types = {}
            for error in self.results["errors"]:
                error_key = error["error"]
                error_types[error_key] = error_types.get(error_key, 0) + 1

            for error_type, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {error_type}: {count}")

            # Show first few errors
            print(f"\nSample Errors (first 5):")
            for error in self.results["errors"][:5]:
                print(
                    f"  User {error['user_id']}, Request {error['request_num']}: "
                    f"{error['error']} (Status: {error['status_code']})"
                )

        print(f"\n{'='*70}\n")

    def export_results(self, filename: str):
        """Export results to JSON file."""
        export_data = {
            **self.results,
            "start_time": self.results["start_time"].isoformat(),
            "end_time": self.results["end_time"].isoformat(),
            "config": {
                "base_url": self.base_url,
                "agent_type": self.agent_type,
                "num_users": self.num_users,
                "requests_per_user": self.requests_per_user,
            },
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"Results exported to: {filename}")


async def main():
    parser = argparse.ArgumentParser(
        description="Load test Strands A2A agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test calculator agent with 100 users
  python load_test.py --url http://localhost:9000 --password mypass --users 100

  # Test factor agent with 250 users
  python load_test.py --url http://localhost:9001 --password mypass --users 250 --agent factor

  # Custom requests per user
  python load_test.py --url https://my-agent.com --password mypass --users 100 --requests 10

  # Export results
  python load_test.py --url http://localhost:9000 --password mypass --users 100 --output results.json
        """,
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of the agent (e.g., http://localhost:9000)",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="API password for authentication (or set API_PASSWORD env var)",
    )
    parser.add_argument(
        "--agent",
        choices=["calculator", "factor"],
        default="calculator",
        help="Agent type to test (default: calculator)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=100,
        help="Number of concurrent users (default: 100)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=5,
        help="Requests per user (default: 5)",
    )
    parser.add_argument(
        "--output",
        help="Export results to JSON file (optional)",
    )

    args = parser.parse_args()

    # Create and run load tester
    tester = LoadTester(
        base_url=args.url,
        api_password=args.password,
        agent_type=args.agent,
        num_users=args.users,
        requests_per_user=args.requests,
    )

    try:
        await tester.run_load_test()
        tester.print_results()

        if args.output:
            tester.export_results(args.output)

    except KeyboardInterrupt:
        print("\n\nLoad test interrupted by user")
        if tester.results["total_requests"] > 0:
            tester.print_results()
    except Exception as e:
        print(f"\nError during load test: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
