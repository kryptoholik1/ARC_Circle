"""Arca automated evaluator — wired to our own ArcaEscrow contract.

For each job this evaluator is assigned to, once the provider has SUBMITTED a
deliverable it:
  1. checks out the referenced repo @ the submitted commit,
  2. runs the acceptance test suite (the objective oracle),
  3. if green -> calls ArcaEscrow.release(jobId), paying the agent in USDC.
  Red tests -> nothing happens; the escrow stays locked.

The on-chain job only stores hashes (acceptanceHash, deliverableHash) — the repo
URL + test command live off-chain in a task map (here a dict; in production an
indexer or the job description). This is the piece that turns the escrow into a
real product: no human approves, the tests do.

Usage:
  python evaluator/arca_evaluator.py            # poll assigned jobs once
Reads RPC/keys from .env (EVALUATOR_PRIVATE_KEY), ABI from contracts/.
"""
import json
import os
import sys
from pathlib import Path

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from evaluator.run_tests import run as run_tests  # noqa: E402

RPC = os.environ.get("ARC_TESTNET_RPC_URL", "https://rpc.testnet.arc.io")
EXPLORER = os.environ.get("ARC_TESTNET_EXPLORER", "https://explorer.testnet.arc.io")
ESCROW = Web3.to_checksum_address(json.loads((ROOT / "contracts" / "deployments.json").read_text())["ArcaEscrow"]["testnet"]["address"])
ABI = json.loads((ROOT / "contracts" / "ArcaEscrow.abi.json").read_text())

w3 = Web3(Web3.HTTPProvider(RPC))
evaluator = Account.from_key(os.environ["EVALUATOR_PRIVATE_KEY"])
escrow = w3.eth.contract(address=ESCROW, abi=ABI)

STATUS = {0: "Open", 1: "Claimed", 2: "Submitted", 3: "Released", 4: "Refunded"}


def _send(fn):
    tx = fn.build_transaction({
        "from": evaluator.address, "nonce": w3.eth.get_transaction_count(evaluator.address, "pending"),
        "chainId": w3.eth.chain_id, "maxFeePerGas": max(w3.eth.gas_price * 2, Web3.to_wei(20, "gwei")),
        "maxPriorityFeePerGas": Web3.to_wei(1, "gwei")})
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.3)
    r = w3.eth.wait_for_transaction_receipt(
        w3.eth.send_raw_transaction(evaluator.sign_transaction(tx).raw_transaction), timeout=120)
    assert r.status == 1, "tx reverted"
    return r


def evaluate_and_settle(job_id: int, repo: str, ref: str, test_cmd: str):
    """Run the acceptance tests for a submitted job and release if they pass."""
    j = escrow.functions.getJob(job_id).call()
    status, job_evaluator = j[5], j[2]
    print(f"job {job_id}: status={STATUS.get(status)} evaluator={job_evaluator}")
    if status != 2:
        print("  not in Submitted state — skipping"); return False
    if job_evaluator.lower() != evaluator.address.lower():
        print("  not our job to evaluate — skipping"); return False

    print(f"  running acceptance check: `{test_cmd}` on {repo}@{ref}")
    passed, log = run_tests(repo, ref, test_cmd)
    print("  " + log.strip().splitlines()[-1] if log.strip() else "  (no output)")
    if not passed:
        print("  ❌ tests FAILED — escrow stays locked, no payout")
        return False

    print("  ✅ tests PASSED — releasing USDC to the agent")
    r = _send(escrow.functions.release(job_id))
    print(f"  released: {EXPLORER}/tx/{r.transactionHash.hex()}")
    return True


if __name__ == "__main__":
    # Task map: jobId -> where the work lives + how to verify it.
    # In production this comes from an indexer / the job description; here it's explicit.
    TASKS = json.loads(os.environ.get("ARCA_TASKS", "{}"))
    if not TASKS:
        print("Set ARCA_TASKS='{\"<jobId>\": {\"repo\":\"...\",\"ref\":\"...\",\"test_cmd\":\"pytest -q\"}}'")
        sys.exit(0)
    for jid, t in TASKS.items():
        evaluate_and_settle(int(jid), t["repo"], t.get("ref", "HEAD"), t.get("test_cmd", "pytest -q"))
