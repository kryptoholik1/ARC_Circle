"""Tiny helper for signing and sending EIP-1559 transactions on Arc.

Gas on Arc is paid in native USDC (18 decimals internally). Arc enforces a
maxFeePerGas floor of 20 gwei, so we set a sane floor here.
"""
from web3 import Web3

MIN_MAX_FEE = Web3.to_wei(20, "gwei")   # Arc maxFeePerGas floor
PRIORITY_FEE = Web3.to_wei(1, "gwei")


def send(w3, account, fn_call, value: int = 0):
    """Build, sign and send a contract function call. Returns the receipt."""
    base = w3.eth.gas_price
    max_fee = max(base * 2, MIN_MAX_FEE)
    tx = fn_call.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address, "pending"),
        "chainId": w3.eth.chain_id,
        "value": value,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": PRIORITY_FEE,
    })
    # estimate gas with a small buffer
    try:
        tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.25)
    except Exception:
        tx["gas"] = 500_000
    signed = account.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  → sent {h.hex()}  (waiting for finality…)")
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
    status = "OK" if rcpt.status == 1 else "FAILED"
    print(f"  ← {status} in block {rcpt.blockNumber}")
    if rcpt.status != 1:
        raise RuntimeError(f"tx reverted: {h.hex()}")
    return rcpt


def simulate_uint(fn_call, sender):
    """Call a state-changing fn read-only to capture its uint return (e.g. jobId)."""
    return fn_call.call({"from": sender})
