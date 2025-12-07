Agents
======

What’s here
-----------
- `src/butler/` — primary Butler agent tools and behaviors (posting jobs, RAG, slot filling).
- `src/caller/` — ElevenLabs caller server and voice agent entrypoints.
- `src/manager/` — coordinator/manager services.
- `src/shared/` — shared infrastructure (contracts, NeoFS, events, wallets, embeddings).
- `src/tiktok/` — TikTok-specific agents/tools.
- `spoonos_butler_api.py` — API surface for Butler.
- `start_butler.py` / `start_butler_api.sh` — launch scripts.
- `requirements*.txt` — Python dependencies.

How to run caller (voice bridge)
--------------------------------
Environment (examples):
```
CALLER_PRIVATE_KEY=...      # wallet for on-chain ops
NEOX_RPC_URL=...            # NeoX RPC
ORDERBOOK_ADDRESS=...       # contract
ESCROW_ADDRESS=...
JOB_REGISTRY_ADDRESS=...
AGENT_REGISTRY_ADDRESS=...
REPUTATION_TOKEN_ADDRESS=...
USDC_ADDRESS=...
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...
CALL_SUMMARY_WEBHOOK_URL=http://localhost:3001/api/calls
CALL_SUMMARY_SECRET=...
ELEVENLABS_WEBHOOK_SECRET=...
PYTHONPATH=.
```
Start:
```
uvicorn agents.src.caller.server:app --host 0.0.0.0 --port 3003
```

How to post jobs (Butler)
-------------------------
- Uses NeoFS for metadata via `PostJobTool` (see `src/butler/tools.py`).
- Contracts wired via `src/shared/contracts.py` and env vars (`NEOX_PRIVATE_KEY`, contract addresses).

Notes
-----
- NeoFS helper scripts: `create_neofs_container.py`, `neofs_storage.py`.
- Tests/scripts live under `test_*` and `verify_contracts.py`. 
