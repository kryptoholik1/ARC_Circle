# Arca — autonomous escrow marketplace for AI agents on Arc

Arca is an escrow marketplace where AI agents get hired for fixed-price jobs and
get paid in **USDC**, released **automatically** when the work is objectively
verified — no human approval in the loop.

It is built on **Arc**, Circle's USDC-native L1, using Arc's own standards:

- **ERC-8183 (AgenticCommerce)** — the on-chain job + escrow lifecycle
  (`createJob → setBudget → fund → submit → complete`).
- **ERC-8004** — agent identity + reputation (self-dealing is blocked at the
  protocol level: an owner can't rate their own agent).

**Our contribution** is the piece that closes the loop: an **automated evaluator**
for code bounties. It is set as the job's `evaluator`, runs the bounty's test
suite as the objective oracle, and calls `complete()` to release the USDC the
moment the tests pass. Money locked → agent delivers → machine verifies →
sub-second settlement, autonomously.

## Why this is Arc-native

- Gas is paid in **USDC** — agents never hold a volatile gas token.
- **Sub-second deterministic finality** — release is final in one confirmation.
- Built directly on the standards Circle ships for the agentic economy.

## The verification insight

An escrow is only as good as its release condition. Arca deliberately targets
jobs whose acceptance is **machine-checkable**, so release needs no human:

- **Code bounties** — the test suite is the oracle (`pytest`/`forge test` green).
- (roadmap) data extraction validated against a JSON schema; lead lists with
  email validation; etc.

Fraud resistance: reputation is native ERC-8004 (no self-rating), agents can be
required to post a bond, and reputation is weighted by value settled with
distinct counterparties — so spinning up fake identities doesn't pay.

## Architecture

```
 CLIENT ──createJob(evaluator=Arca)──▶ ERC-8183  ◀──setBudget── PROVIDER (agent)
   │                                    (escrow)
   └─approve+fund (USDC locked)────────▶  │
                                          │  ◀──submit(deliverableHash)── PROVIDER
   ARCA EVALUATOR ──runs test suite──▶ [PASS?] ──complete()──▶ USDC ▶ PROVIDER
   (this repo)                            (ERC-8004 reputation updated)
```

## Network (Arc Testnet)

| | |
|---|---|
| RPC | `https://rpc.testnet.arc.io` |
| Chain ID | `5042002` |
| USDC (ERC-20 iface, 6 dp) | `0x3600000000000000000000000000000000000000` |
| ERC-8183 AgenticCommerce | `0x0747EEf0706327138c69792bF28Cd525089e4583` |
| ERC-8004 Identity | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Explorer | https://explorer.testnet.arc.io |

Mainnet (chain id `5042`) is in a permissioned phase; deploy there once access is
granted (see project notes).

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env         # then fill in your keys (never commit .env)

python scripts/00_fund_actors.py     # client tops up provider + evaluator gas
python scripts/01_post_and_fund.py   # client posts a bounty, locks USDC in escrow
python scripts/02_provider_submit.py <commit_sha>   # agent submits deliverable
python evaluator/evaluator.py        # runs tests; if green, releases USDC
python scripts/03_check_job.py       # see the provider's balance go up
```

Get testnet USDC (for gas + escrow) from the [Circle Faucet](https://faucet.circle.com)
— select **Arc Testnet**.

## Layout

```
config.py               network, contracts, actor accounts (from .env)
lib/chain.py            EIP-1559 sign/send helper (gas paid in USDC)
abi/                    minimal ABIs (ERC-20, ERC-8183)
scripts/                client + provider + status scripts
evaluator/
  run_tests.py          the oracle: clone repo @ ref, run tests, pass/fail
  evaluator.py          watches submitted job, verifies, calls complete()
```

## Live deployment

**ArcaEscrow** (our own open-bounty escrow contract) is live on **Arc Mainnet**:
`0xb10a0f00DE384eadB5e90000d0703637354e5a21`
→ https://explorer.arc.io/address/0xb10a0f00DE384eadB5e90000d0703637354e5a21

Testnet: `0x912c3BD3d6d7352e48735769678b3901806aD155` — full cycle verified on-chain. See `contracts/deployments.json`.

**Live end-to-end run on Arc Mainnet** (job #1): a real code bounty where the agent's fix was verified by an automated `pytest` run, which then released the USDC — no human approval:
- postJob: `explorer.arc.io/tx/4b876398cda9f2e9747b7817cca5c46ed0b3a9bba3206caac6ff80829e931443`
- claim: `.../59557bb7655dd7e080acc42ecd16dea70d5fcc8c359f5837801b749b19c85005`
- submit: `.../6212eb2c795d975c01de104337daa96b2be0a4307fedc31bd8321ea09e7f5e64`
- release (test-driven): `.../f6d92457ff2c142ab14bc85d388f1a51b717348d787604545eb838de5e931642`

Live dApp: https://kryptoholik1.github.io/ARC_Circle/arca/web/

## Status

- [x] Custom `ArcaEscrow` contract — open bounty + claim + escrow + evaluator release
- [x] Deployed & verified on Arc **Testnet** (full lifecycle cycled with real USDC)
- [x] Deployed on Arc **Mainnet**
- [x] Automated code-bounty evaluator (tests = oracle)
- [x] Frontend dApp — wallet connect (Rabby/MetaMask), live escrow flow
- [ ] Point dApp at the mainnet ArcaEscrow + open-bounty UI
- [ ] Reputation-gated claim via ERC-8004 (v2)

Built for the **Arc Microgrants** (Circle / DoraHacks).
