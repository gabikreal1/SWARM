# Agent Event-Driven Architecture

## Overview
Manager, Scraper, and Caller agents are **event-driven workers** that:
1. **Listen** to `JobPosted` events from the OrderBook
2. **Evaluate** if they can fulfill the job
3. **Bid** with a detailed proposal if profitable
4. **Execute** when their bid is accepted

## Architecture Pattern

```
┌─────────────────┐
│   OrderBook     │
│  (Smart Contract)│
└────────┬────────┘
         │ emits JobPosted(jobId, poster)
         ▼
┌─────────────────────────────────┐
│   Event Listener (Polling)      │
│   setup_event_listener()        │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Agent Evaluates Job            │
│  1. Fetch job details           │
│  2. Check capabilities match    │
│  3. LLM: "Can I do this?"       │
│  4. Calculate cost + margin     │
└────────┬────────────────────────┘
         │
         ├─ No → Ignore
         │
         └─ Yes → Place Bid
                  ▼
         ┌─────────────────────────┐
         │  Generate Bid Metadata  │
         │  - Approach/strategy    │
         │  - Deliverables         │
         │  - Timeline estimate    │
         │  - Questions (if any)   │
         └────────┬────────────────┘
                  │
                  ▼
         ┌─────────────────────────┐
         │   place_bid()           │
         │   - price               │
         │   - deliveryTime        │
         │   - metadataURI         │
         └─────────────────────────┘
```

## Implementation Pattern

### 1. Event Listener Setup
```python
from agents.src.shared.contracts import get_contracts, setup_event_listener

contracts = get_contracts(private_key)

def on_job_posted(event):
    job_id = event['args']['jobId']
    poster = event['args']['poster']
    
    # Don't bid on own jobs
    if poster == contracts.account.address:
        return
    
    # Evaluate and potentially bid
    evaluate_and_bid(job_id)

setup_event_listener(contracts, "JobPosted", on_job_posted)
```

### 2. Job Evaluation
```python
def evaluate_and_bid(job_id: int):
    # Fetch full job details
    job_state, existing_bids = contracts.order_book.functions.getJob(job_id).call()
    
    # Parse job
    poster = job_state[0]
    status = job_state[1]
    description = "..."  # Would need to fetch from metadata_uri
    
    # Check capabilities
    if not can_handle_job(description):
        print(f"⏭️  Job {job_id}: Not in my capabilities")
        return
    
    # LLM-based evaluation
    evaluation = llm_evaluate_job(description)
    if not evaluation['can_do']:
        print(f"⏭️  Job {job_id}: {evaluation['reason']}")
        return
    
    # Calculate bid
    base_cost = evaluation['estimated_cost']
    margin = 0.15  # 15% profit margin
    bid_price = int(base_cost * (1 + margin))
    estimated_time = evaluation['estimated_hours'] * 3600
    
    # Generate proposal metadata
    metadata = {
        "approach": evaluation['approach'],
        "deliverables": evaluation['deliverables'],
        "questions": evaluation.get('questions', []),
        "timeline": evaluation['timeline']
    }
    metadata_uri = upload_to_ipfs(metadata)  # or Arweave
    
    # Submit bid
    place_bid(
        contracts,
        job_id=job_id,
        amount=bid_price,
        estimated_time=estimated_time,
        metadata_uri=metadata_uri
    )
```

### 3. LLM Evaluation (Example)
```python
def llm_evaluate_job(description: str) -> dict:
    """Use LLM to evaluate if agent can do the job and at what cost."""
    
    prompt = f"""
    You are a {AGENT_TYPE} agent. Evaluate this job:
    
    Description: {description}
    
    Your capabilities: {CAPABILITIES}
    
    Respond in JSON:
    {{
        "can_do": true/false,
        "reason": "explanation",
        "estimated_cost": 100,  // USD value
        "estimated_hours": 2,
        "approach": "How you'll do it",
        "deliverables": ["What you'll deliver"],
        "questions": ["Any clarifications needed"],
        "timeline": "2 hours"
    }}
    """
    
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
```

## Bid Metadata Structure

The `metadataURI` should point to a JSON file with:

```json
{
  "agent": {
    "type": "scraper",
    "version": "1.0.0",
    "address": "0x..."
  },
  "proposal": {
    "approach": "I will use Bright Data API to scrape the target TikTok profile @username, collecting the last 100 posts with engagement metrics.",
    "deliverables": [
      "JSON file with 100 TikTok posts",
      "Engagement metrics (likes, comments, shares)",
      "Creator profile information",
      "Uploaded to NeoFS with proof hash"
    ],
    "timeline": "Estimated 2 hours",
    "tools": ["Bright Data", "NeoFS"]
  },
  "questions": [
    "Do you need video URLs or just metadata?",
    "Should I include comments data?"
  ],
  "pricing": {
    "base_cost": 15,
    "margin": 0.15,
    "total": 17.25
  }
}
```

## Agent Types & Capabilities

### Scraper Agent
- **Bids on:** `TIKTOK_SCRAPE`, `WEB_SCRAPE`
- **Evaluation:** Can I access the target? Do I have API credits?
- **Cost factors:** API usage, data volume, rate limits

### Caller Agent
- **Bids on:** `CALL_VERIFICATION`
- **Evaluation:** Can I make calls in this region? Do I have Twilio credits?
- **Cost factors:** Call duration, international rates

### Manager Agent
- **Special case:** Manager posts jobs, does NOT bid
- **Role:** Orchestrates complex jobs by posting sub-tasks

## Next Steps

To implement full agents:
1. **Scraper Agent:** `agents/src/scraper/agent.py` already has the structure
2. **Caller Agent:** `agents/src/caller/agent.py` similar pattern
3. **Manager Agent:** `agents/src/manager/agent.py` posts jobs instead of bidding

Each needs:
- Event listener setup
- LLM-based job evaluation
- Metadata generation (IPFS/Arweave)
- Execution logic when bid is accepted
