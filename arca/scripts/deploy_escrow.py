"""Compile and deploy ArcaEscrow to Arc (testnet or mainnet).

Usage:
  NETWORK=testnet python scripts/deploy_escrow.py
  NETWORK=mainnet python scripts/deploy_escrow.py

Reads DEPLOYER key from .env (PRIVATE_KEY). Gas is paid in native USDC.
Compiler: solc 0.8.24, evmVersion=paris (max Arc compatibility).
"""
import json, os, sys
from pathlib import Path

import solcx
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

NET = os.environ.get("NETWORK", "testnet")
RPC = "https://rpc.mainnet.arc.io" if NET == "mainnet" else "https://rpc.testnet.arc.io"
EXP = "https://explorer.arc.io" if NET == "mainnet" else "https://explorer.testnet.arc.io"
USDC = Web3.to_checksum_address("0x3600000000000000000000000000000000000000")

def main():
    solcx.install_solc("0.8.24")
    src = (ROOT / "contracts" / "ArcaEscrow.sol").read_text()
    comp = solcx.compile_source(src, output_values=["abi", "bin"], solc_version="0.8.24", evm_version="paris")
    key = [k for k in comp if k.endswith(":ArcaEscrow")][0]
    abi, bytecode = comp[key]["abi"], comp[key]["bin"]

    w = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    dep = Account.from_key(os.environ["PRIVATE_KEY"])
    print(f"{NET} chainId={w.eth.chain_id} deployer={dep.address} gas={w.eth.get_balance(dep.address)/1e18:.4f} USDC")

    C = w.eth.contract(abi=abi, bytecode=bytecode)
    tx = C.constructor(USDC).build_transaction({
        "from": dep.address, "nonce": w.eth.get_transaction_count(dep.address, "pending"),
        "chainId": w.eth.chain_id, "maxFeePerGas": max(w.eth.gas_price * 2, Web3.to_wei(20, "gwei")),
        "maxPriorityFeePerGas": Web3.to_wei(1, "gwei")})
    tx["gas"] = int(w.eth.estimate_gas(tx) * 1.3)
    s = dep.sign_transaction(tx)
    r = w.eth.wait_for_transaction_receipt(w.eth.send_raw_transaction(s.raw_transaction), timeout=180)
    assert r.status == 1, "deploy reverted"
    print(f"ArcaEscrow deployed: {r.contractAddress}")
    print(f"{EXP}/address/{r.contractAddress}")

if __name__ == "__main__":
    main()
