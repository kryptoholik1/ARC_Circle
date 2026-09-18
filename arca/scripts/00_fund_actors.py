"""Send a little gas USDC from the client wallet to the provider and evaluator,
so all three roles can transact. Run once. Testnet only.

Usage:  python scripts/00_fund_actors.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as cfg
from lib.chain import send

GAS_TOPUP = 3 * 10 ** 6   # 3 USDC (ERC-20, 6 decimals) each — plenty for gas on testnet


def main():
    client = cfg.CLIENT
    assert client, "CLIENT/PRIVATE_KEY missing in .env"
    for role, acct in [("PROVIDER", cfg.PROVIDER), ("EVALUATOR", cfg.EVALUATOR)]:
        if not acct:
            print(f"skip {role}: no key")
            continue
        native = cfg.w3.eth.get_balance(acct.address)
        print(f"{role} {acct.address}  native gas balance: {native/10**18:.4f} USDC")
        if native > 0:
            print("  already funded, skipping")
            continue
        print(f"  transferring {GAS_TOPUP/10**6} USDC to {role} for gas…")
        send(cfg.w3, client, cfg.usdc.functions.transfer(acct.address, GAS_TOPUP))
    print("done.")


if __name__ == "__main__":
    main()
