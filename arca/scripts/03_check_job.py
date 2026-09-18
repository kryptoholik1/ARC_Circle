"""Show the current demo state and the provider's USDC balance, so you can see the
escrow release land after the evaluator settles.

Usage:  python scripts/03_check_job.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as cfg

STATE = Path(__file__).resolve().parent.parent / ".job_state.json"


def bal(addr):
    return cfg.usdc.functions.balanceOf(addr).call() / 10 ** 6


def main():
    if STATE.exists():
        st = json.loads(STATE.read_text())
        print("job state:", json.dumps(st, indent=2))
        print(f"provider  {st['provider']}  USDC = {bal(st['provider']):.2f}")
        print(f"evaluator {st['evaluator']}  USDC = {bal(st['evaluator']):.2f}")
    print(f"client    {cfg.CLIENT.address}  USDC = {bal(cfg.CLIENT.address):.2f}")
    print(f"market    {cfg.link_addr(cfg.AGENTIC_COMMERCE)}")


if __name__ == "__main__":
    main()
