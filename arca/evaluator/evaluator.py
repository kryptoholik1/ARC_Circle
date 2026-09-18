"""Arca automated evaluator — the heart of the project.

For a submitted code bounty, it:
  1. reads the job (repo + ref + test command),
  2. runs the test suite via run_tests.run() (the objective oracle),
  3. if green -> calls complete(jobId, reasonHash) on ERC-8183, releasing USDC to
     the provider. No human approves; the tests do.

This is what closes the autonomous "agentic economy" loop: money is locked, an
agent delivers, machine verification settles it on-chain in sub-second finality.

Usage:  python evaluator/evaluator.py
Reads .job_state.json produced by the earlier steps.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

import config as cfg
from lib.chain import send
from evaluator.run_tests import run as run_tests

STATE = Path(__file__).resolve().parent.parent / ".job_state.json"


def evaluate(job):
    print(f"Evaluating job {job['jobId']}: {job['repo']} @ {job.get('commit','HEAD')}")
    passed, log = run_tests(job["repo"], job.get("commit", "HEAD"), job["test_cmd"])
    print(log[-1500:])
    return passed


def main():
    assert cfg.EVALUATOR, "EVALUATOR_PRIVATE_KEY missing in .env"
    job = json.loads(STATE.read_text())

    passed = evaluate(job)
    if not passed:
        print("\n❌ Acceptance criteria NOT met — escrow stays locked. "
              "Provider can resubmit, or client disputes after the deadline.")
        return

    print("\n✅ Tests pass — releasing escrow to provider via complete()")
    reason = Web3.keccak(text="tests-passed")  # bytes32 audit reason
    send(cfg.w3, cfg.EVALUATOR,
         cfg.market.functions.complete(job["jobId"], reason, b""))
    print(f"USDC released to provider {job['provider']}. Loop closed autonomously.")


if __name__ == "__main__":
    main()
