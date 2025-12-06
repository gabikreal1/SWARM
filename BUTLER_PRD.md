## Butler AI PRD (SpoonOS)

### Goal
Voice- and text-first Butler that answers arbitrary user questions via RAG and, when actions are needed, collects structured intent and dispatches to OrderBook selecting the best downstream agent by cost/reputation. Uses ElevenLabs for voice I/O, OpenAI for LLM/embeddings, Qdrant for RAG, Mem0 for long-term/context memory.

### Scope (v1)
- Channel: Voice (ElevenLabs) + text (web/mobile).
- Domain: Generic Q&A with RAG; action path starts with refining users intent on what he needs from the agentic market.
- Retrieval: Qdrant collections (e.g., `butler_restaurant_kb` plus future domain KBs); Mem0 collections `butler_restaurant_kb_global` (+ per-user when available).
- Action: For actionable requests, collect slots, confirm, and dispatch to OrderBook with agent selection by cost/reputation; for pure Q&A, answer directly from RAG.

### Non-goals (v1)
- Payments/cancellations handling end-to-end.
- Multi-lingual voice.
- Complex travel/booking beyond restaurants.

### User flows
1) User speaks or types request (any question/task).
2) Butler retrieves context (Qdrant/Mem0) and answers directly if informational; if action-oriented, checks missing slots, asks clarifying questions (<=3 at a time).
3) Once slots complete, Butler summarizes and asks for confirmation.
4) On “yes”, Butler queries OrderBook agents, scores by reputation/cost, dispatches task with structured payload.
5) Returns status/next steps; logs to memory.

### System components
- **LLM**: OpenAI (chat + `text-embedding-3-small`).
- **Slot/questioning**: `slot_questioning.py` (tool-required + memory-derived slots, EmbeddingModel, Mem0 + Qdrant).
- **RAG**: Qdrant (`butler_restaurant_kb`, payload `privacy` indexed, embeddings 1536-d), Mem0 (`butler_restaurant_kb_global`, per-user optional).
- **OrderBook connector**: Lists agents, scores by cost/reputation, submits tasks.
- **Voice I/O**: ElevenLabs ASR → Butler; Butler → ElevenLabs TTS.
- **NeoFS**: Decentralized storage for job metadata (requirements, constraints) and delivery results (scraped data, call logs). Uses NeoX testnet REST Gateway.
- **Router (optional)**: If multi-agent, route by capability/intent; otherwise Butler is primary.

### Data & collections
- Qdrant: `butler_restaurant_kb` (anonymized/global), vectors from OpenAI embeddings.
- Mem0: `butler_restaurant_kb_global` (anonymized), plus per-user namespaces for preferences if desired.
- Slot templates: Stored via Mem0/Qdrant (from `slot_questioning.py`) to speed slot inference.

### Pipelines
**Inference pipeline**
1) Ingress (voice/text) with `user_id`/session.
2) RAG: Qdrant search (privacy filter), Mem0 search (user → global).
3) SlotFiller: tool-required + memory-derived slots; generate questions.
4) LLM response: incorporate RAG context + slot prompts; ask/confirm.
5) NeoFS Upload: Butler uploads job details (requirements, constraints, expected deliverables) to NeoFS → gets `metadataURI`.
6) Dispatch: if confirmed and slots complete → OrderBook.postJob(description, metadataURI, tags, deadline) with agent scoring.
7) Agent Execution: Worker agents fetch job details from NeoFS, execute task, upload results to NeoFS → get `deliveryURI`.
8) Agent Delivery: Worker calls OrderBook.submitDelivery(jobId, keccak256(deliveryURI)).
9) Egress: Butler fetches results from NeoFS, formats response → TTS for voice; stream for chat.
10) Persistence: log to Mem0 (per-user/global), optional Qdrant template upsert.

**Seeding pipeline**
- `seed_knowledge.py`: seeds restaurant booking KB to Qdrant/Mem0 (anonymized), uses OpenAI embeddings.
- Extend `SEED_ITEMS` for more domains; rerun to upsert.

### Configuration
- Env keys: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `MEM0_API_KEY`, OrderBook endpoint/creds, ElevenLabs creds.
- Embedding dimension fixed to 1536 (OpenAI). Avoid mixing hash fallback in production.
- Collections: Qdrant `butler_restaurant_kb`; Mem0 `butler_restaurant_kb_global` (+ per-user).
- SlotFiller: max questions=3; tool-required slots prioritized.

### Agent patterns
- **Graph**: deterministic nodes for slot collection → retrieval → confirmation → dispatch; clearer control.
- **ReAct**: flexible tool use for FAQs/edge cases; can be an escape hatch.
- Recommended: Graph for core booking path, ReAct for off-path questions, then return to graph.

### Tooling to attach
- `slot_questioning` tool (missing slots + questions).
- `rag_search` tool (Qdrant/Mem0 lookup for KB).
- `orderbook_dispatch` tool (list agents, score, submit).
- Validators (date/time parsing, location normalization).

### Scoring for OrderBook agents
- Example: `score = w_rep * reputation - w_cost * cost`, filter by capability/uptime. Default weights configurable; require minimum reputation threshold.

### Error handling
- If ASR low confidence → ask to repeat.
- If RAG/memory unavailable → fall back to tool-required slots only.
- If OrderBook fails → return apology + offer to retry later; log incident.

### Security/Privacy
- Keep `.env` gitignored; never log secrets.
- Respect per-user vs anonymized storage; avoid leaking user PII into global collections.
- Confirm before dispatching tasks on behalf of user.

### Testing
- Unit: slot ranking, RAG wrapper, agent scoring.
- Integration: end-to-end voice/text → slots → RAG → confirmation → mock OrderBook dispatch.
- Load/smoke: concurrency on API endpoints; TTS/ASR latency checks.

### Rollout
- Phase 1: Text-only beta with mock OrderBook.
- Phase 2: Enable real OrderBook dispatch; monitor costs and success rate.
- Phase 3: Enable voice path via ElevenLabs; monitor ASR errors and user drop-off.

### Monitoring
- Log: requests, toolcalls, dispatch decisions, errors.
- Metrics: slot completion rate, clarification turns per task, dispatch success/failure, ASR confidence, cost per task, reputation scores chosen.
