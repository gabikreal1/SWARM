Prisma
======

What’s here
-----------
- `schema.prisma` — data model (Postgres).
- `migrations/` — migration history.
- `seed.ts` / `seed.js` — seed scripts.
- `pgdump.sql` — dump snapshot.

Quick start
-----------
Install (from repo root):
```
npm install
```

Set env (example `.env`):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/swarm?schema=public
```

Run migrations:
```
npx prisma migrate deploy
```

Inspect / studio:
```
npx prisma studio
```

Notes
-----
- Development DB file at `prisma/prisma/dev.db` if using SQLite; otherwise use `DATABASE_URL`.
- Migrations include `20251206114442_init` and `20251207041642_add_call_summaries`.
