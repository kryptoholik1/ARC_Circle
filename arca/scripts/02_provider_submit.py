"""PROVIDER submits the deliverable hash, moving the job to Submitted.

The deliverable hash commits the provider to a specific result (e.g. a git commit
SHA). The evaluator later checks the work behind that hash and settles.

Usage:  python scripts/02_provider_submit.py <git_commit_sha>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

import config as cfg
from lib.chain import send

STATE = Path(__file__).resolve().parent.parent / ".job_state.json"


def main():
    st = json.loads(STATE.read_text())
    commit = sys.argv[1] if len(sys.argv) > 1 else "demo-deliverable"
    deliverable_hash = Web3.keccak(text=commit)   # bytes32 commitment to the work
    print(f"submit jobId={st['jobId']} commit={commit}")
    send(cfg.w3, cfg.PROVIDER,
         cfg.market.functions.submit(st["jobId"], deliverable_hash, b""))
    st["commit"] = commit
    st["deliverable_hash"] = deliverable_hash.hex()
    STATE.write_text(json.dumps(st, indent=2))
    print("submitted. Evaluator can now verify and settle.")


if __name__ == "__main__":
    main()
