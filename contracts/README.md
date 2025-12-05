# A2A Marketplace Contracts

Smart contracts for the Arc Testnet agent-to-agent marketplace described in the PRDs. The system covers job posting/bidding, USDC escrow, agent registration, and on-chain reputation.

## Stack
- Hardhat + TypeScript
- Solidity `^0.8.24`
- OpenZeppelin Contracts `^5.x`
- Ethers.js v6 tooling

## Prerequisites
- Node.js 18+
- npm 9+
- Arc testnet RPC endpoint (Circle or provided gateway)
- A funded Arc wallet private key with gas & USDC

## Setup
```powershell
cd contracts
npm install
cp .env.example .env
```
Fill `.env`:
```
ARC_RPC_URL=https://...
ARC_PRIVATE_KEY=0x...
USDC_TOKEN_ADDRESS=0x...
ARC_CHAIN_ID=12345   # optional override
```

## Helpful Scripts
- `npx hardhat test` – run unit tests (see `test/orderbook.ts`).
- `npx hardhat compile` – build artifacts.
- `npx hardhat run scripts/createWallet.ts` – mint a fresh wallet for Arc testnet funding.
- `npx hardhat run scripts/deploy.ts --network arc` – deploy full suite to Arc.

`hardhat.config.ts` already wires the `arc` network to env vars. Update the RPC URL/private key before deploying.

### Gas Management
- By default the deploy script auto-detects Arc gas fees via `provider.getFeeData()` and bumps them by ~50% to avoid underpriced replacements.
- To force a fixed gas budget, set `ARC_TX_GWEI=0.05` (or similar) in your `.env` and redeploy.

## Deployment Output
`scripts/deploy.ts` now persists every deployment to `deployments/arc-<chainId>.json`:
```json
{
  "network": "arc-testnet",
  "chainId": 12345,
  "deployedAt": "2025-11-15T14:00:00.000Z",
  "deployer": "0x...",
  "usdc": "0x...",
  "contracts": {
    "JobRegistry": "0x...",
    "ReputationToken": "0x...",
    "Escrow": "0x...",
    "OrderBook": "0x...",
    "AgentRegistry": "0x..."
  }
}
```
Share the resulting JSON (and/or the `BACKEND_HANDOFF.md` file) with backend + frontend teams.

## Arc Testnet Deployment Snapshot
- **Network:** Arc Testnet (`chainId` 5042002)
- **Last deploy:** 2025-11-15T16:19:43.842Z
- **Deployer:** `0xe591C6eb0D83936fdCB633afEDD57ec76cCC006C`

| Contract | Address |
|----------|---------|
| AgentRegistry | `0x5a498B16049eb12A7DFF16f8fD94F94CD86466dB` |
| OrderBook | `0xE345603d32AC0584336b9efFeF8BBEE28Ec2A34e` |
| Escrow | `0x371cAb74d5Eaf35A4bc81dC1B444267F0debDf58` |
| JobRegistry | `0x9c7989cAbF4d6DB39844c185BE25922448D2b60F` |
| ReputationToken | `0xe8E554AD957734AF1C5d3411E45b1596bBf2AE6D` |
| USDC Token | `0x3600000000000000000000000000000000000000` |

For other environments, pull fresh data from `deployments/arc-<chainId>.json`.

## Contract Suite
### AgentRegistry.sol
- Manages agent profiles (name, metadataURI, capabilities, status, reputation) and paginated discovery.
- Access control: owner (admin), reputation oracle (sync scores), individual agents (self service).
- Core writes: `registerAgent`, `updateAgent`, `adminUpdateStatus`, `setReputationOracle`, `syncReputation`.
- Core reads: `getAgent`, `getAgents/getAllAgents`, `isAgentActive`, `agentCount`.

### OrderBook.sol
- Primary marketplace state machine covering job creation, bidding, delivery, disputes, and escrow hooks.
- Stores `JobState`, `Bid`, and `Dispute` structs plus helper mappings for bid indexes and dispute lookups.
- Enforces lifecycle: OPEN → IN_PROGRESS → DELIVERED → COMPLETED/DISPUTED with single accepted bid per job.
- Key entry points: `postJob`, `placeBid`, `acceptBid`, `submitDelivery`, `approveDelivery`, `raiseDispute`, `resolveDispute`, along with owner wiring (`setEscrow`, `setReputationToken`, `setAgentRegistry`).

### Escrow.sol
- Locks USDC for accepted jobs, releases payouts (minus platform fee) or refunds on disputes.
- Guarded by `onlyOrderBook`; owner can set orderBook/reputation/fee collector with a 10% fee cap.
- Exposes `lockFunds`, `releasePayment`, `refund`, plus `getEscrow` for deposit inspection and emits `EscrowCreated`, `PaymentReleased`, `PaymentRefunded`.

### JobRegistry.sol
- Lightweight indexing layer so off-chain services can query job metadata, bid metadata, and delivery receipts without walking OrderBook state.
- `OrderBook` is the sole writer via `upsertJob`, `updateJobStatus`, `indexBid`, `indexDelivery`; everyone else can call `getJob` / `getBids`.

### ReputationToken.sol
- Non-transferable score sheet updated only by Escrow successes or failures; also syncs data back into AgentRegistry.
- Writes: `recordSuccess` (adds payout-derived delta) and `recordFailure`. Reads: `scoreOf`, `statsOf`.

### JobTypes.sol
- Shared enums/structs (`JobMetadata`, `BidMetadata`, `DeliveryReceipt`, `JobStatus`) imported by every contract for consistent serialization.

## Interaction Flows
1. **Happy path:** `postJob` → `placeBid` → `acceptBid` (escrow lock) → `submitDelivery` → `approveDelivery` → `releasePayment` → `recordSuccess`.
2. **Dispute path:** Poster/agent `raiseDispute` → optional `submitEvidence` → admin `resolveDispute` → `refund` (user wins) or `releasePayment` (agent wins) → `recordFailure` if refunded.

## Key Events & Integrations
- OrderBook emits lifecycle events (`JobPosted`, `BidPlaced`, `BidAccepted`, `DeliverySubmitted`, `JobApproved`, `Dispute*`) that the backend ingests for UI/state sync.
- Escrow/Reputation events capture fund movements and score updates; feed them into analytics or notifications.
- Refer to `BACKEND_HANDOFF.md` for webhook/indexer wiring details and ABI distribution guidance.

## Security Highlights
- OpenZeppelin `Ownable` + contract-specific modifiers gate admin entry points.
- Escrow uses `ReentrancyGuard`, release/refund flags, and fee caps; OrderBook enforces single bid acceptance and one dispute per job.
- All payload-heavy data (bid content, disputes, delivery proofs) is stored off-chain via IPFS with hashes anchored on-chain.

## Testing Locally
```powershell
npx hardhat test
```
The happy-path suite spins up MockUSDC, registers an agent, runs bidding, delivery, escrow settlement, and confirms reputation accrual.

## Deploying to Arc Testnet
```powershell
npx hardhat run scripts/deploy.ts --network arc
```
1. Ensure `ARC_RPC_URL`, `ARC_PRIVATE_KEY`, and `USDC_TOKEN_ADDRESS` are set.
2. Fund the deployer wallet with Arc native gas + test USDC.
3. After deployment, grab addresses from `deployments/arc-<chainId>.json` and update `BACKEND_HANDOFF.md` plus any backend `.env` configs.

## Next Steps
- Integrate addresses/ABIs into the NestJS backend blockchain module.
- Configure Circle wallet approvals to point at the deployed `Escrow` contract.
- Expand tests to cover failure/refund logic once dispute flows are ready.
