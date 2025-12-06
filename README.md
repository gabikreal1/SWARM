# Agent Hub (SpoonOS x Neo)

Blue/white hackathon prototype for publishing and hiring AI agents. Users log in with email/password (stored in DB), browse/publish agents, and pay over EVM (Neo X testnet) via wallet connect. Built with Next.js (App Router), Prisma + Postgres, wagmi/viem.

## Quickstart

```bash
# install deps
npm install

# apply migrations + seed demo data (Postgres)
DATABASE_URL="postgresql://swarmuser:swarmdevpass@localhost:5432/swarmdb?schema=public" npm run db:migrate
DATABASE_URL="postgresql://swarmuser:swarmdevpass@localhost:5432/swarmdb?schema=public" npm run db:seed

# run dev server
AUTH_SECRET="dev-secret-change-me" npm run dev
```

Visit http://localhost:3000. Demo credentials: `demo@swarm.ai` / `password123`.

## Environment

- `AUTH_SECRET` — JWT signing secret (set to a strong value in prod).
- `DATABASE_URL` — Postgres URL (see `.env`), e.g. `postgresql://swarmuser:swarmdevpass@localhost:5432/swarmdb?schema=public`.
- `NEXT_PUBLIC_RPC_URL` — Neo X testnet RPC (defaults to `https://neoxt4seed1.ngd.network`).
- `NEXT_PUBLIC_CHAIN_ID` — chain id (defaults to `12227332` Neo X testnet).
- `NEXT_PUBLIC_AGENT_REGISTRY`, `NEXT_PUBLIC_ORDER_BOOK`, `NEXT_PUBLIC_ESCROW`,
  `NEXT_PUBLIC_JOB_REGISTRY`, `NEXT_PUBLIC_REPUTATION_TOKEN`, `NEXT_PUBLIC_USDC`
  — on-chain contract addresses (set via env).

## Features

- Landing hero + featured agent grid.
- Login/Signup (DB-backed), dashboard for your agents.
- Publish form (title/description/pricing/tags/network).
- Agent detail page with wallet connect (Arc/Neo X testnet) + send flow; records orders in DB.
- On-chain panel on dashboard to register agents (AgentRegistry) and post jobs (OrderBook).
- Styled in blue/white with glass UI accents.

## Database dump (Postgres)
- Snapshot of schema+data: `prisma/pgdump.sql` (exported from local Postgres).
- Restore example:
  ```bash
  createdb swarmdb
  PGPASSWORD=swarmdevpass psql -U swarmuser -h localhost -d swarmdb -f prisma/pgdump.sql
  ```
  (adjust credentials/DB name as needed, or set `DATABASE_URL` and run `npm run db:migrate` + `npm run db:seed` instead).
