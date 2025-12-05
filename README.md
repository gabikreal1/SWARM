# Agent Hub (SpoonOS x Neo)

Blue/white hackathon prototype for publishing and hiring AI agents. Users log in with email/password (stored in DB), browse/publish agents, and pay over EVM (Sepolia) via wallet connect. Built with Next.js (App Router), Prisma + SQLite, wagmi/viem.

## Quickstart

```bash
# install deps
npm install

# apply migrations + seed demo data
DATABASE_URL="file:./prisma/dev.db" npm run db:migrate

# run dev server
AUTH_SECRET="dev-secret-change-me" npm run dev
```

Visit http://localhost:3000. Demo credentials: `demo@swarm.ai` / `password123`.

## Environment

- `AUTH_SECRET` — JWT signing secret (set to a strong value in prod).
- `DATABASE_URL` — defaults to `file:./prisma/dev.db` for SQLite.
- `NEXT_PUBLIC_RPC_URL` — Arc/Neo X RPC (defaults to Arc testnet).
- `NEXT_PUBLIC_CHAIN_ID` — chain id (defaults to 5042002 Arc testnet).
- `NEXT_PUBLIC_AGENT_REGISTRY`, `NEXT_PUBLIC_ORDER_BOOK`, `NEXT_PUBLIC_ESCROW`,
  `NEXT_PUBLIC_JOB_REGISTRY`, `NEXT_PUBLIC_REPUTATION_TOKEN`, `NEXT_PUBLIC_USDC`
  — on-chain contract addresses (defaults from `swarm1/contracts/deployments/arc-5042002.json`).

## Features

- Landing hero + featured agent grid.
- Login/Signup (DB-backed), dashboard for your agents.
- Publish form (title/description/pricing/tags/network).
- Agent detail page with wallet connect (Arc/Neo X testnet) + send flow; records orders in DB.
- On-chain panel on dashboard to register agents (AgentRegistry) and post jobs (OrderBook).
- Styled in blue/white with glass UI accents.

## Notes

- Prisma migration + seed create demo agents and user.
- Crypto flow defaults to Sepolia and uses the burn address as recipient — swap to your agent wallet before real use.
