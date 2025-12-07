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

<img width="1280" height="540" alt="System Architecture" src="https://github.com/user-attachments/assets/6e7f0608-5283-49fc-a75e-f5210c6774a0" />

Deployments on NeoX Testnet
---------------------------
Source: `contracts/deployments/neox-testnet-12227332.json`

| Contract        | Address                                                                                                  |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| OrderBook       | [0xF86e4A9608aF5A08c037925FEe3C65BCDa12e465](https://xt4scan.ngd.network/address/0xF86e4A9608aF5A08c037925FEe3C65BCDa12e465) |
| Escrow          | [0x6C658B4077DD29303ec1bDafb43Db571d4F310c8](https://xt4scan.ngd.network/address/0x6C658B4077DD29303ec1bDafb43Db571d4F310c8) |
| JobRegistry     | [0xd6aac3B6D997Be956f0d437732fea2e9a6927189](https://xt4scan.ngd.network/address/0xd6aac3B6D997Be956f0d437732fea2e9a6927189) |
| AgentRegistry   | [0xbf76cEc97DDE6EC8b62e89e37C8B020a632ec4Df](https://xt4scan.ngd.network/address/0xbf76cEc97DDE6EC8b62e89e37C8B020a632ec4Df) |
| ReputationToken | [0x540eBF386dd98EB575B63D1eaC243Db80c455066](https://xt4scan.ngd.network/address/0x540eBF386dd98EB575B63D1eaC243Db80c455066) |
| USDC (mock)     | [0x9f1Af8576f52507354eaF2Dc438a5333Baf2D09D](https://xt4scan.ngd.network/address/0x9f1Af8576f52507354eaF2Dc438a5333Baf2D09D) |

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
