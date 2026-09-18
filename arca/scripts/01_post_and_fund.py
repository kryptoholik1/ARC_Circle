"""CLIENT posts a code bounty and funds the escrow; PROVIDER sets the budget.

Flow (ERC-8183):
  client:   createJob(provider, evaluator, expiredAt, description, hook=0x0)  -> jobId
  provider: setBudget(jobId, amount)
  client:   USDC.approve(market, amount)  then  fund(jobId)

The `evaluator` is set to OUR automated evaluator address — that's what makes the
release autonomous later (evaluator.py runs the tests and calls complete()).

Usage:  python scripts/01_post_and_fund.py
Writes the resulting jobId to .job_state.json for the next steps.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

import config as cfg
from lib.chain import send, simulate_uint

STATE = Path(__file__).resolve().parent.parent / ".job_state.json"

# --- the demo bounty ---
BUDGET = 5 * 10 ** 6          # 5 USDC (6 decimals)
DESCRIPTION = "Fix failing test suite in demo repo — release on green CI"
DELIVERABLE_REPO = "https://github.com/YOUR_ORG/arca-demo-bounty"
TEST_CMD = "pytest -q"


def main():
    client, provider, evaluator = cfg.CLIENT, cfg.PROVIDER, cfg.EVALUATOR
    assert client and provider and evaluator, "need CLIENT, PROVIDER, EVALUATOR keys in .env"
    expired_at = int(time.time()) + 7 * 24 * 3600  # 7-day deadline

    print("1) createJob (client)")
    create_fn = cfg.market.functions.createJob(
        provider.address, evaluator.address, expired_at, DESCRIPTION,
        "0x0000000000000000000000000000000000000000",
    )
    job_id = simulate_uint(create_fn, client.address)   # predict returned jobId
    send(cfg.w3, client, create_fn)
    print(f"   jobId = {job_id}")

    print("2) setBudget (provider)")
    send(cfg.w3, provider, cfg.market.functions.setBudget(job_id, BUDGET, b""))

    print("3) approve USDC (client)")
    send(cfg.w3, client, cfg.usdc.functions.approve(cfg.AGENTIC_COMMERCE, BUDGET))

    print("4) fund escrow (client)")
    send(cfg.w3, client, cfg.market.functions.fund(job_id, b""))

    STATE.write_text(json.dumps({
        "jobId": job_id,
        "budget": BUDGET,
        "repo": DELIVERABLE_REPO,
        "test_cmd": TEST_CMD,
        "provider": provider.address,
        "evaluator": evaluator.address,
    }, indent=2))
    print(f"\nEscrow funded with {BUDGET/10**6} USDC. State saved to {STATE.name}")


if __name__ == "__main__":
    main()
