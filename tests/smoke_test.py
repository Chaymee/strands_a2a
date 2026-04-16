#!/usr/bin/env python3
"""
Smoke test and workshop concurrency tester for Strands A2A agents.

Two modes:

  health   - Quick check that both agents are alive (1 request each, ~5-10s).
             Run this before a workshop to confirm everything is up.

  workshop - Simulates N concurrent attendees all hitting an agent at once.
             All requests fire simultaneously and results print as they land.
             Good for confirming the agent stays responsive under real workshop load.

Usage:
    # Pre-workshop health check (both agents)
    python smoke_test.py health --calculator http://host:9000 --clock http://host:9001 --password pw

    # Simulate 15 workshop attendees hitting the calculator agent
    python smoke_test.py workshop --url http://host:9000 --password pw --agent calculator --users 15

    # Simulate 20 attendees hitting the clock agent
    python smoke_test.py workshop --url http://host:9001 --password pw --agent clock --users 20
"""

import argparse
import asyncio
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

SLOW_THRESHOLD_S = 10.0   # flag responses slower than this
TIMEOUT_S = 45.0           # treat anything longer as a hang

CALCULATOR_MESSAGES = [
    "What is 12 * 12?",
    "Calculate 144 / 12",
    "What is 99 + 1?",
    "What is 256 - 128?",
    "Calculate 7 * 8",
    "What is 1000 / 4?",
    "What is 33 + 67?",
    "Calculate 15 * 15",
]

CLOCK_MESSAGES = [
    "What time is it in UTC?",
    "What is the current time in Tokyo?",
    "What time is it in New York?",
    "What is the current time in London?",
    "What time is it in Sydney?",
    "What is the current time in Los Angeles?",
    "What time is it in Paris?",
    "What is the current time in Singapore?",
]


@dataclass
class Result:
    user_id: int
    success: bool
    status_code: Optional[int]
    elapsed: float
    error: Optional[str] = None

    @property
    def label(self) -> str:
        if not self.success:
            if self.error and "timeout" in self.error.lower():
                return "TIMEOUT"
            return "FAIL"
        if self.elapsed > SLOW_THRESHOLD_S:
            return "SLOW"
        return "OK"

    @property
    def color(self) -> str:
        return {"OK": "\033[32m", "SLOW": "\033[33m", "TIMEOUT": "\033[31m", "FAIL": "\033[31m"}[self.label]


RESET = "\033[0m"
BOLD = "\033[1m"


def _make_payload(message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "messageId": str(uuid.uuid4()),
            }
        },
    }


async def send_one(session: aiohttp.ClientSession, url: str, password: str, message: str, user_id: int) -> Result:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {password}",
    }
    start = time.time()
    try:
        async with session.post(
            url,
            json=_make_payload(message),
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
        ) as resp:
            elapsed = time.time() - start
            await resp.read()  # consume body
            return Result(
                user_id=user_id,
                success=resp.status == 200,
                status_code=resp.status,
                elapsed=elapsed,
                error=None if resp.status == 200 else f"HTTP {resp.status}",
            )
    except asyncio.TimeoutError:
        return Result(user_id=user_id, success=False, status_code=None,
                      elapsed=time.time() - start, error="timeout")
    except Exception as exc:
        return Result(user_id=user_id, success=False, status_code=None,
                      elapsed=time.time() - start, error=str(exc))


async def check_agent_card(session: aiohttp.ClientSession, url: str) -> tuple[bool, str]:
    try:
        async with session.get(
            f"{url.rstrip('/')}/.well-known/agent-card.json",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return True, data.get("name", "unknown")
            return False, f"HTTP {resp.status}"
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Health mode
# ---------------------------------------------------------------------------

async def run_health(calculator_url: str, clock_url: str, password: str):
    print(f"\n{BOLD}=== Pre-workshop Health Check ==={RESET}\n")

    agents = [
        ("Calculator", calculator_url, CALCULATOR_MESSAGES[0]),
        ("Clock",       clock_url,       CLOCK_MESSAGES[0]),
    ]

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        all_ok = True
        for name, url, message in agents:
            print(f"  Checking {name} at {url} ...")

            # agent card
            ok, card_name = await check_agent_card(session, url)
            if ok:
                print(f"    Agent card: {card_name}")
            else:
                print(f"    \033[31mAgent card FAILED: {card_name}{RESET}")
                all_ok = False
                continue

            # live request
            result = await send_one(session, url, password, message, user_id=0)
            color = result.color
            print(f"    Live request: {color}{result.label}{RESET}  ({result.elapsed:.1f}s)", end="")
            if result.error:
                print(f"  [{result.error}]", end="")
            print()

            if not result.success:
                all_ok = False

            print()

    print(f"{BOLD}Result: {'ALL GOOD' if all_ok else 'ONE OR MORE AGENTS FAILED'}{RESET}\n")
    return all_ok


# ---------------------------------------------------------------------------
# Workshop simulation mode
# ---------------------------------------------------------------------------

async def run_workshop(url: str, password: str, agent: str, num_users: int):
    messages = CALCULATOR_MESSAGES if agent == "calculator" else CLOCK_MESSAGES

    import random
    user_messages = [random.choice(messages) for _ in range(num_users)]

    print(f"\n{BOLD}=== Workshop Simulation ==={RESET}")
    print(f"  Agent:   {agent} at {url}")
    print(f"  Users:   {num_users} (all fire simultaneously)")
    print(f"  Timeout: {TIMEOUT_S}s per request")
    print(f"  Slow threshold: {SLOW_THRESHOLD_S}s\n")

    results: list[Result] = []
    lock = asyncio.Lock()

    async def user_task(session: aiohttp.ClientSession, user_id: int, message: str):
        result = await send_one(session, url, password, message, user_id)
        async with lock:
            results.append(result)
            # Print result as it lands
            idx = len(results)
            color = result.color
            status_str = f"HTTP {result.status_code}" if result.status_code else (result.error or "?")
            print(f"  [{idx:>2}/{num_users}] user-{user_id:>3}  {color}{result.label:<7}{RESET}  "
                  f"{result.elapsed:>5.1f}s  {status_str}")

    connector = aiohttp.TCPConnector(limit=num_users + 5)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Verify the agent is up first
        ok, card_name = await check_agent_card(session, url)
        if not ok:
            print(f"\033[31mAgent card check failed: {card_name}{RESET}")
            sys.exit(1)
        print(f"  Agent card OK: {card_name}\n")

        wall_start = time.time()
        tasks = [user_task(session, i, user_messages[i]) for i in range(num_users)]
        await asyncio.gather(*tasks)
        wall_elapsed = time.time() - wall_start

    # Summary
    ok_count      = sum(1 for r in results if r.label == "OK")
    slow_count    = sum(1 for r in results if r.label == "SLOW")
    timeout_count = sum(1 for r in results if r.label == "TIMEOUT")
    fail_count    = sum(1 for r in results if r.label == "FAIL")
    success_count = ok_count + slow_count

    times = [r.elapsed for r in results]
    mean_t  = sum(times) / len(times)
    median_t = sorted(times)[len(times) // 2]
    p95_t   = sorted(times)[int(len(times) * 0.95)]

    print(f"\n{BOLD}--- Summary ---{RESET}")
    print(f"  Wall time:   {wall_elapsed:.1f}s")
    print(f"  Success:     \033[32m{success_count}/{num_users}\033[0m"
          f"  (OK: {ok_count}, slow >{SLOW_THRESHOLD_S}s: {slow_count})")
    if timeout_count:
        print(f"  Timeouts:    \033[31m{timeout_count}\033[0m")
    if fail_count:
        print(f"  Errors:      \033[31m{fail_count}\033[0m")
    print(f"  Response times:  mean {mean_t:.1f}s  median {median_t:.1f}s  p95 {p95_t:.1f}s")

    if timeout_count > 0:
        print(f"\n  \033[31mWARNING: {timeout_count} request(s) timed out after {TIMEOUT_S}s.")
        print(f"  The agent may be hanging under load. Check server logs.{RESET}")
    elif slow_count > num_users // 3:
        print(f"\n  \033[33mNOTE: More than a third of requests were slow (>{SLOW_THRESHOLD_S}s).")
        print(f"  The agent is responding but may struggle under full workshop load.{RESET}")
    elif success_count == num_users:
        print(f"\n  \033[32mAll {num_users} users succeeded. Agent is ready for the workshop.{RESET}")

    print()
    return success_count == num_users


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Smoke test and workshop load simulator for Strands A2A agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # health subcommand
    health_p = sub.add_parser("health", help="Pre-workshop health check (both agents)")
    health_p.add_argument("--calculator", default="http://localhost:9000",
                          help="Calculator Agent URL (default: http://localhost:9000)")
    health_p.add_argument("--clock", default="http://localhost:9001",
                          help="Clock Agent URL (default: http://localhost:9001)")
    health_p.add_argument("--password", required=True, help="API password")

    # workshop subcommand
    ws_p = sub.add_parser("workshop", help="Simulate N concurrent workshop attendees")
    ws_p.add_argument("--url", required=True, help="Agent URL to test")
    ws_p.add_argument("--password", required=True, help="API password")
    ws_p.add_argument("--agent", choices=["calculator", "clock"], default="calculator",
                      help="Agent type (determines test messages, default: calculator)")
    ws_p.add_argument("--users", type=int, default=15,
                      help="Number of concurrent users (default: 15)")

    args = parser.parse_args()

    if args.mode == "health":
        ok = asyncio.run(run_health(args.calculator, args.clock, args.password))
        sys.exit(0 if ok else 1)
    else:
        ok = asyncio.run(run_workshop(args.url, args.password, args.agent, args.users))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
