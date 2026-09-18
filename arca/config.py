"""Central config for Arca — loads .env, builds the web3 client, contracts and actor accounts.

Arca is an escrow marketplace for AI agents built on Arc's native standards:
  - ERC-8183 (AgenticCommerce) — job + escrow lifecycle
  - ERC-8004 — agent identity + reputation
Our contribution: an automated evaluator that releases USDC when a code bounty's
test suite passes — no human in the loop.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- network ---
RPC_URL = os.environ.get("ARC_TESTNET_RPC_URL", "https://rpc.testnet.arc.io")
CHAIN_ID = int(os.environ.get("ARC_TESTNET_CHAIN_ID", "5042002"))
EXPLORER = os.environ.get("ARC_TESTNET_EXPLORER", "https://explorer.testnet.arc.io")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# --- addresses ---
USDC = Web3.to_checksum_address(os.environ["USDC_ADDRESS"])
AGENTIC_COMMERCE = Web3.to_checksum_address(os.environ["ERC8183_AGENTIC_COMMERCE_TESTNET"])

# --- ABIs ---
_ABI = ROOT / "abi"
ERC20_ABI = json.loads((_ABI / "erc20.json").read_text())
AGENTIC_ABI = json.loads((_ABI / "agentic_commerce.json").read_text())

usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)
market = w3.eth.contract(address=AGENTIC_COMMERCE, abi=AGENTIC_ABI)


def _acct(env_key: str, fallback: str | None = None):
    pk = os.environ.get(env_key) or (os.environ.get(fallback) if fallback else None)
    return Account.from_key(pk) if pk else None


# Roles. Client falls back to the main PRIVATE_KEY if CLIENT_PRIVATE_KEY is unset.
CLIENT = _acct("CLIENT_PRIVATE_KEY", "PRIVATE_KEY")
PROVIDER = _acct("PROVIDER_PRIVATE_KEY")
EVALUATOR = _acct("EVALUATOR_PRIVATE_KEY")


def link_tx(tx_hash: str) -> str:
    return f"{EXPLORER}/tx/{tx_hash}"


def link_addr(addr: str) -> str:
    return f"{EXPLORER}/address/{addr}"
