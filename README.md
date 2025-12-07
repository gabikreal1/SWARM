SWARM Monorepo
==============

Overview
--------
- AI Butler voice and web stack: ElevenLabs caller, Butler agents, on-chain OrderBook/Escrow, NeoFS metadata, and Next.js UI.
- Repo entry points:
  - `agents/` — Python agents (caller/voice bridge, Butler, manager, shared infra). See `agents/README.md`.
  - `contracts/` — Solidity contracts + Hardhat. See `contracts/README.md`.
  - `mobile_frontend/` — Next.js voice UI and dashboard. See `mobile_frontend/README.md`.
  - `prisma/` — Prisma schema/migrations. See `prisma/README.md`.
  - `src/` — Next.js app (dashboard + APIs).

Demo video
----------
- Demo: https://youtu.be/ojpjAW3RyLM

Architecture
------------
![System Architecture](assets/telegram-cloud-document-4-5884099775271279458-945afe32-517b-4cb1-9bc6-237fe88cdf8a.png)

Deployments On NeoX TestNet
---------------------
Chain: `12227332`

| Contract          | Address                                                                                               |
| ----------------- | ------------------------------------------------------------------------------------------------------ |
| OrderBook         | [0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9](https://xt4scan.ngd.network/address/0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9) |
| Escrow            | [0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9](https://xt4scan.ngd.network/address/0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9) |
| JobRegistry       | [0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512](https://xt4scan.ngd.network/address/0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512) |
| AgentRegistry     | [0x5FC8d32690cc91D4c39d9d3abcBD16989F875707](https://xt4scan.ngd.network/address/0x5FC8d32690cc91D4c39d9d3abcBD16989F875707) |
| ReputationToken   | [0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0](https://xt4scan.ngd.network/address/0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0) |
| USDC (mock)       | [0x5FbDB2315678afecb367f032d93F642f64180aa3](https://xt4scan.ngd.network/address/0x5FbDB2315678afecb367f032d93F642f64180aa3) |

Quick commands
--------------
- Caller voice server: `uvicorn agents.src.caller.server:app --host 0.0.0.0 --port 3003`
- Frontend: `cd mobile_frontend && npm run dev -- --hostname localhost --port 3002`
- Contracts: `cd contracts && npx hardhat compile`
- Prisma migrate: `npx prisma migrate deploy`

Env pointers (NeoX testnet examples)
------------------------------------
- `NEOX_RPC_URL=https://testnet.rpc.banelabs.org`
- `ORDERBOOK_ADDRESS`, `ESCROW_ADDRESS`, `JOB_REGISTRY_ADDRESS`, `AGENT_REGISTRY_ADDRESS`, `REPUTATION_TOKEN_ADDRESS`, `USDC_ADDRESS`
- ElevenLabs: `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, webhook secrets
