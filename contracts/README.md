Contracts
=========

What’s here
-----------
- `contracts/` — Solidity sources (OrderBook, Escrow, JobRegistry, AgentRegistry, ReputationToken, JobTypes).
- `integrations/spoon/` — ABIs and helper scripts for downstream consumers.
- `deployments/` — saved deployment artifacts per network.
- `artifacts/`, `typechain-types/` — build outputs.
- `scripts/` — Hardhat scripts (deploy, verify).
- `test/` — Hardhat tests.

Quick start
-----------
Install deps:
```
cd contracts
npm install
```

Build & test:
```
npx hardhat compile
npx hardhat test
```

Deploy (example):
```
npx hardhat run scripts/deploy.ts --network neox-testnet
```

Key contracts
-------------
- `OrderBook.sol` — job lifecycle, bids, acceptance, delivery signaling.
- `Escrow.sol` — funds lock/release for accepted bids.
- `JobRegistry.sol` — indexed job/bid metadata (metadataURI stored here).
- `AgentRegistry.sol` — agent allowlisting/activation.
- `ReputationToken.sol` — agent reputation scoring (viewed by OrderBook).

Metadata note
-------------
When posting jobs, `metadataURI` is passed to `OrderBook.postJob` and stored in `JobRegistry.upsertJob`. Fetch metadata via `JobRegistry.getJob(jobId).metadata.metadataURI`. 
