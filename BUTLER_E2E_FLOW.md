# Butler End-to-End Flow with NeoFS

## Complete Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────────┐
│   User      │────▶│  ElevenLabs  │────▶│   Butler   │────▶│  Blockchain  │
│  (Voice)    │◀────│    Agent     │◀────│    API     │◀────│  + NeoFS     │
└─────────────┘     └──────────────┘     └────────────┘     └──────────────┘
                                                │                    │
                                                │                    │
                                                ▼                    ▼
                                          ┌────────────┐      ┌────────────┐
                                          │   Qdrant   │      │   Worker   │
                                          │   + Mem0   │      │   Agents   │
                                          └────────────┘      └────────────┘
```

## Flow Breakdown

### **Phase 1: User Inquiry** 
*(User speaks → ElevenLabs → Butler `/inquire`)*

```
USER: "I need to scrape 100 TikTok posts from @elonmusk"
  ↓
ElevenLabs Agent detects intent
  ↓
POST /api/spoonos/inquire
{
  "query": "I need to scrape 100 TikTok posts from @elonmusk",
  "user_id": "user_123",
  "session_id": "session_456"
}
  ↓
Butler API Processing:
  1. RAG: Search Qdrant for similar jobs/knowledge
  2. SlotFiller: Extract required parameters
     - Tool: "tiktok_scrape"
     - Slots: {username: "@elonmusk", count: 100}
  3. Check if all required slots filled
  
  IF missing_slots:
    → Return clarifying question
  ELSE:
    → Return "Ready to get quote"
  ↓
Response to ElevenLabs:
{
  "status": "ready",
  "text": "I have all details for tiktok_scrape. Shall I get a quote?",
  "slots": {"username": "@elonmusk", "count": 100},
  "tool": "tiktok_scrape",
  "description": "Scrape TikTok @elonmusk for 100 posts",
  "tags": ["tiktok_scrape"]
}
  ↓
ElevenLabs: "Got it! I found all the details. Getting quotes from available agents..."
```

**Current Code:**
```python
@app.post("/api/spoonos/inquire")
async def inquire(request: InquireRequest):
    # 1. RAG: Search knowledge base
    # 2. SlotFiller: Extract parameters
    # 3. Return questions OR ready status
```

---

### **Phase 2: Get Quote** 
*(ElevenLabs → Butler `/quote` → NeoFS → Blockchain)*

```
ElevenLabs calls:
POST /api/spoonos/quote
{
  "description": "Scrape TikTok @elonmusk for 100 posts",
  "tags": ["tiktok", "scraping"],
  "deadline": 3600,  // 1 hour
  "requirements": {
    "username": "@elonmusk",
    "count": 100,
    "fields": ["likes", "comments", "shares"]
  }
}
  ↓
Butler API Processing:

┌─────────────────────────────────────────┐
│ Step 1: Upload Metadata to NeoFS       │
└─────────────────────────────────────────┘
  Create job_metadata = {
    "description": "Scrape TikTok...",
    "requirements": {...},
    "constraints": {"max_time": 3600, "budget": 50},
    "timestamp": 1733501234
  }
    ↓
  UploadObjectTool.execute(
    container_id=NEOFS_CONTAINER_ID,
    content=json.dumps(job_metadata),
    attributes={"type": "job_metadata"}
  )
    ↓
  Result: object_id = "Fxyz123..."
    ↓
  metadata_uri = "neofs://CID/Fxyz123..."

┌─────────────────────────────────────────┐
│ Step 2: Post Job to OrderBook          │
└─────────────────────────────────────────┘
  OrderBook.postJob(
    description = "Scrape TikTok @elonmusk for 100 posts",
    metadataURI = "neofs://CID/Fxyz123...",  ← NeoFS link!
    tags = ["tiktok", "scraping"],
    deadline = timestamp + 3600
  )
    ↓
  Emits: JobPosted(jobId=123, poster=Butler, ...)
    ↓
  job_id = 123

┌─────────────────────────────────────────┐
│ Step 3: Agents React to Event          │
└─────────────────────────────────────────┘
  Worker Agent (listening):
    1. Hears JobPosted(123)
    2. Calls OrderBook.getJob(123)
       → Gets metadataURI = "neofs://CID/Fxyz123..."
    3. Downloads from NeoFS:
       DownloadObjectByIdTool.execute(container_id, object_id)
       → Gets full job_metadata
    4. LLM Evaluation:
       "Can I scrape TikTok? Do I have Bright Data API? Yes!"
    5. Calculates price: $15 USDC
    6. Places bid:
       OrderBook.placeBid(
         jobId=123,
         amount=15 * 10^6,  // USDC decimals
         estimatedTime=7200,  // 2 hours
         metadataURI="neofs://CID/proposal_xyz"  ← Agent's proposal
       )

┌─────────────────────────────────────────┐
│ Step 4: Butler Polls Bids (after 8s)   │
└─────────────────────────────────────────┘
  await asyncio.sleep(8)  // Wait for bids
    ↓
  bids = OrderBook.getJob(123)
    → JobState + Bid[]
    ↓
  bids = [
    Bid(id=1, amount=15000000, bidder=0xABC, metadataURI="neofs://..."),
    Bid(id=2, amount=20000000, bidder=0xDEF, metadataURI="neofs://...")
  ]
    ↓
  best_bid = min(bids, key=lambda b: b.amount)
    → Bid(id=1, amount=15000000, ...)

┌─────────────────────────────────────────┐
│ Step 5: Return Quote to User           │
└─────────────────────────────────────────┘
Response to ElevenLabs:
{
  "job_id": 123,
  "metadata_uri": "neofs://CID/Fxyz123...",
  "best_offer": {
    "agent": "0xABC...",
    "price_usdc": 15.0,
    "delivery_time_hours": 2.0,
    "proposal_uri": "neofs://CID/proposal_xyz"
  },
  "total_bids": 2
}
  ↓
ElevenLabs: "I found 2 agents. Best offer is $15 from Agent 0xABC, 
             estimated 2 hours. Would you like to proceed?"
```

**Updated Code:**
```python
@app.post("/api/spoonos/quote")
async def get_quote(request: QuoteRequest):
    # Step 1: Upload job metadata to NeoFS
    upload_tool = UploadObjectTool()
    neofs_object_id = await upload_tool.execute(
        container_id=os.getenv("NEOFS_CONTAINER_ID"),
        content=json.dumps(job_metadata),
        attributes_json='{"type": "job_metadata"}'
    )
    metadata_uri = f"neofs://{CONTAINER_ID}/{neofs_object_id}"
    
    # Step 2: Post to blockchain with NeoFS URI
    job_id = post_job(contracts, description, metadata_uri, tags, deadline)
    
    # Step 3: Wait for agents to bid
    await asyncio.sleep(8)
    
    # Step 4: Get bids
    job_state, bids = get_bids_for_job(contracts, job_id)
    
    # Step 5: Return best offer
    return {"job_id": job_id, "best_offer": {...}}
```

---

### **Phase 3: Confirm & Accept**
*(User confirms → ElevenLabs → Butler `/confirm`)*

```
ElevenLabs hears: "Yes, accept that offer"
  ↓
POST /api/spoonos/confirm
{
  "job_id": 123,
  "bid_id": 1
}
  ↓
Butler API Processing:

┌─────────────────────────────────────────┐
│ Step 1: Accept Bid on Blockchain       │
└─────────────────────────────────────────┘
  OrderBook.acceptBid(
    jobId=123,
    bidId=1,
    responseURI=""  // Optional feedback
  )
    ↓
  Emits: BidAccepted(jobId=123, bidId=1, agent=0xABC)
    ↓
  Escrow.lockFunds(job=123, amount=15 USDC)
    → Locks payment until delivery

┌─────────────────────────────────────────┐
│ Step 2: Agent Starts Work               │
└─────────────────────────────────────────┘
  Worker Agent (listening):
    1. Hears BidAccepted(123, 1)
    2. Confirms it's their bid
    3. Downloads job metadata from NeoFS again
    4. Starts execution:
       - Calls Bright Data API
       - Scrapes @elonmusk TikTok
       - Collects 100 posts with likes/comments/shares

Response to ElevenLabs:
{
  "status": "accepted",
  "job_id": 123,
  "bid_id": 1,
  "agent": "0xABC...",
  "message": "Agent accepted! They'll start work now. 
              Estimated delivery in 2 hours."
}
  ↓
ElevenLabs: "Great! Agent 0xABC is now working on your task. 
             I'll notify you when it's done."
```

**Code:**
```python
@app.post("/api/spoonos/confirm")
async def confirm_job(request: ConfirmRequest):
    # Accept bid on-chain
    accept_bid(contracts, request.job_id, request.bid_id, "")
    
    return {
        "status": "accepted",
        "message": "Agent will start work now"
    }
```

---

### **Phase 4: Agent Execution** 
*(Background, no Butler involvement)*

```
Agent executes job independently:

┌─────────────────────────────────────────┐
│ Step 1: Scrape TikTok                   │
└─────────────────────────────────────────┘
  posts = []
  for i in range(100):
    post = bright_data.scrape_tiktok_post(...)
    posts.append(post)

┌─────────────────────────────────────────┐
│ Step 2: Upload Results to NeoFS        │
└─────────────────────────────────────────┘
  results = {
    "job_id": 123,
    "posts": posts,  // 100 posts
    "metrics": {
      "total_likes": 1234567,
      "total_comments": 89012,
      "avg_engagement": 12345.67
    },
    "completed_at": "2025-12-06T10:30:00Z"
  }
    ↓
  UploadObjectTool.execute(
    container_id=NEOFS_CONTAINER_ID,
    content=json.dumps(results),
    attributes={"type": "delivery", "jobId": "123"}
  )
    ↓
  delivery_object_id = "Dabc789..."
    ↓
  delivery_uri = "neofs://CID/Dabc789..."

┌─────────────────────────────────────────┐
│ Step 3: Submit Delivery to Blockchain  │
└─────────────────────────────────────────┘
  proof_hash = keccak256(delivery_uri)
    ↓
  OrderBook.submitDelivery(
    jobId=123,
    proofHash=proof_hash
  )
    ↓
  Emits: DeliverySubmitted(jobId=123, proofHash=...)
    ↓
  Escrow.releasePayment(job=123, to=Agent)
    → Agent receives 15 USDC
```

---

### **Phase 5: Butler Retrieves Results**
*(Butler monitors or user asks)*

```
Option A: Butler monitors DeliverySubmitted events
Option B: User asks "Is my job done?"

┌─────────────────────────────────────────┐
│ Step 1: Check Job Status                │
└─────────────────────────────────────────┘
  job_state, bids = OrderBook.getJob(123)
    → job_state shows "completed"
    ↓
  Find accepted bid
    → bid.metadataURI = "neofs://CID/Dabc789..." (delivery URI)

┌─────────────────────────────────────────┐
│ Step 2: Download Results from NeoFS    │
└─────────────────────────────────────────┘
  DownloadObjectByIdTool.execute(
    container_id=NEOFS_CONTAINER_ID,
    object_id="Dabc789..."
  )
    ↓
  results = {
    "job_id": 123,
    "posts": [...100 posts...],
    "metrics": {...}
  }

┌─────────────────────────────────────────┐
│ Step 3: Format & Return to User        │
└─────────────────────────────────────────┘
Response to ElevenLabs:
{
  "status": "completed",
  "job_id": 123,
  "summary": "Scraped 100 TikTok posts from @elonmusk",
  "metrics": {
    "total_likes": 1234567,
    "avg_engagement": 12345.67
  },
  "download_url": "neofs://CID/Dabc789...",
  "preview": {
    "top_post": {
      "text": "...",
      "likes": 50000
    }
  }
}
  ↓
ElevenLabs: "Your job is complete! I found 100 posts with 1.2M total likes. 
             The most popular post had 50K likes. 
             Would you like me to download the full results?"
```

---

## Key Integration Points

### 1. **Butler ↔ NeoFS**
```python
# Upload job metadata
from spoon_ai.tools.neofs_tools import UploadObjectTool

upload_tool = UploadObjectTool()
object_id = await upload_tool.execute(
    container_id=os.getenv("NEOFS_CONTAINER_ID"),
    content=json.dumps(data),
    attributes_json='{"type": "job_metadata"}'
)

# Download results
from spoon_ai.tools.neofs_tools import DownloadObjectByIdTool

download_tool = DownloadObjectByIdTool()
results = await download_tool.execute(
    container_id=os.getenv("NEOFS_CONTAINER_ID"),
    object_id=object_id
)
```

### 2. **Butler ↔ Blockchain**
```python
# Post job with NeoFS URI
job_id = post_job(
    contracts,
    description="Scrape TikTok...",
    metadata_uri=f"neofs://{container_id}/{object_id}",
    tags=["tiktok"],
    deadline=int(time.time()) + 3600
)

# Accept bid
accept_bid(contracts, job_id, bid_id, "")
```

### 3. **Agent ↔ NeoFS ↔ Blockchain**
```python
# Agent downloads job metadata
job = contracts.order_book.functions.getJob(job_id).call()
metadata = download_from_neofs(job.metadataURI)

# Agent uploads results
result_uri = upload_to_neofs(results)
proof_hash = keccak256(result_uri)
submit_delivery(contracts, job_id, proof_hash)
```

---

## Environment Variables Needed

```env
# Blockchain
NEOX_RPC_URL=https://testnet.rpc.banelabs.org
NEOX_CHAIN_ID=12227332
BUTLER_PRIVATE_KEY=0x...

# NeoFS Storage
NEOFS_CONTAINER_ID=<your_container_id_from_gui>
NEOFS_GATEWAY_URL=https://rest.fs.neo.org

# AI Services
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
MEM0_API_KEY=...
OPENAI_API_KEY=...
```

---

## Testing the Flow

1. **Start Butler API:**
   ```bash
   cd agents
   python spoonos_butler_api.py
   ```

2. **Start Worker Agent:**
   ```bash
   python simple_worker.py
   ```

3. **Test via curl:**
   ```bash
   # Inquire
   curl -X POST http://localhost:8000/api/spoonos/inquire \
     -H "Content-Type: application/json" \
     -d '{"query": "Scrape 100 TikTok posts from @elonmusk"}'
   
   # Quote
   curl -X POST http://localhost:8000/api/spoonos/quote \
     -H "Content-Type: application/json" \
     -d '{"description": "Scrape TikTok @elonmusk", "tags": ["tiktok"], "deadline": 3600}'
   
   # Confirm
   curl -X POST http://localhost:8000/api/spoonos/confirm \
     -H "Content-Type: application/json" \
     -d '{"job_id": 123, "bid_id": 1}'
   ```

---

## Summary

| Phase | User Action | Butler Action | Blockchain/NeoFS |
|-------|-------------|---------------|------------------|
| 1. Inquire | Speaks to ElevenLabs | RAG + SlotFiller | - |
| 2. Quote | "Get quotes" | Upload metadata → Post job → Poll bids | JobPosted event → Agents bid |
| 3. Confirm | "Accept offer" | Accept bid on-chain | BidAccepted → Escrow locks funds |
| 4. Execute | Waits... | - | Agent scrapes → Uploads results → Submits delivery |
| 5. Results | "Is it done?" | Download from NeoFS → Format | DeliverySubmitted → Payment released |

**Key Benefit of NeoFS:** Job requirements and results are stored decentralized, not on-chain. Only URIs are stored on blockchain, keeping gas costs low.
