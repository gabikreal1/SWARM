# NeoFS Integration Guide

## What is NeoFS?

NeoFS is a **decentralized object storage** network built on Neo blockchain. It's used in SpoonOS to store:
1. **Job Metadata**: Detailed requirements, constraints, expected deliverables
2. **Delivery Results**: Scraped data, call logs, analysis reports

## Why NeoFS?

- **Decentralized**: No single point of failure, censorship-resistant
- **Immutable**: Content-addressed storage with proof hashes
- **Neo Integration**: Native integration with NeoX blockchain
- **Cost-effective**: Pay once, store permanently (no recurring fees like AWS S3)

## Testnet Configuration

### NeoFS Testnet REST Gateway
- **URL**: `https://rest.testnet.fs.neo.org`
- **Network**: Neo N3 Testnet (not NeoX, but accessible from NeoX)
- **Free to use**: No credits required for testnet

### Container Setup

You need a NeoFS container (like an S3 bucket) to store objects. For testnet:

**Option 1: Use Pre-created Public Container**
```env
NEOFS_GATEWAY_URL=https://rest.testnet.fs.neo.org
NEOFS_CONTAINER_ID=9iMKzkCQ7TftU6VVKdVGKJiNq3dsY2K8UoFKWzR53ieK
```

**Option 2: Create Your Own Container**
1. Install NeoFS CLI: https://github.com/nspcc-dev/neofs-node/releases
2. Generate wallet: `neofs-cli wallet init -w wallet.json`
3. Fund wallet with testnet GAS: https://neowish.ngd.network/
4. Create container:
   ```bash
   neofs-cli container create \
     --wallet wallet.json \
     --rpc-endpoint grpc://st1.storage.fs.neo.org:8080 \
     --policy "REP 1" \
     --basic-acl public-read-write
   ```

## Data Flow

### 1. Butler Posts Job

```python
# Butler creates job details
job_details = {
    "description": "Scrape TikTok @username",
    "requirements": {
        "target": "@username",
        "count": 100,
        "fields": ["likes", "comments", "shares"]
    },
    "constraints": {
        "max_time": 3600,
        "budget": 20
    },
    "deliverables": [
        "JSON file with posts",
        "Engagement metrics",
        "Upload to NeoFS"
    ]
}

# Upload to NeoFS
neofs_client = NeoFSClient(config)
result = await neofs_client.upload_json(job_details, attributes=[
    ObjectAttribute(key="type", value="job_metadata"),
    ObjectAttribute(key="jobId", value=str(job_id))
])

metadata_uri = f"neofs://{result.container_id}/{result.object_id}"

# Post to OrderBook
job_id = post_job(
    contracts,
    description="TikTok scrape",
    metadata_uri=metadata_uri,
    tags=["tiktok", "scraping"],
    deadline=int(time.time()) + 3600
)
```

### 2. Agent Fetches Job & Evaluates

```python
# Agent listens for JobPosted event
def on_job_posted(event):
    job_id = event['args']['jobId']
    
    # Fetch job from contract
    job_state, bids = contracts.order_book.functions.getJob(job_id).call()
    
    # Parse metadata URI
    # From JobRegistry or parse from event
    metadata_uri = "neofs://container/object"
    
    # Download job details from NeoFS
    job_details = await neofs_client.download_json(metadata_uri)
    
    # Evaluate with LLM
    can_do = evaluate_job(job_details)
    
    if can_do:
        # Create bid proposal
        proposal = {
            "approach": "Use Bright Data API...",
            "tools": ["Bright Data", "NeoFS"],
            "timeline": "2 hours"
        }
        
        # Upload proposal to NeoFS
        proposal_result = await neofs_client.upload_json(proposal)
        proposal_uri = f"neofs://{proposal_result.container_id}/{proposal_result.object_id}"
        
        # Place bid
        place_bid(
            contracts,
            job_id=job_id,
            amount=15,
            estimated_time=7200,
            metadata_uri=proposal_uri
        )
```

### 3. Agent Executes & Delivers

```python
# After bid accepted, agent executes job
def on_bid_accepted(event):
    job_id = event['args']['jobId']
    
    # Execute scraping
    results = scrape_tiktok(username, count=100)
    
    # Upload results to NeoFS
    delivery_result = await neofs_client.upload_json(results, attributes=[
        ObjectAttribute(key="type", value="delivery"),
        ObjectAttribute(key="jobId", value=str(job_id)),
        ObjectAttribute(key="timestamp", value=str(int(time.time())))
    ])
    
    delivery_uri = f"neofs://{delivery_result.container_id}/{delivery_result.object_id}"
    
    # Compute proof hash
    import hashlib
    proof_hash = hashlib.sha256(delivery_uri.encode()).digest()
    
    # Submit delivery to contract
    submit_delivery(contracts, job_id, proof_hash)
```

### 4. Butler Retrieves Results

```python
# Butler monitors DeliverySubmitted event
def on_delivery_submitted(event):
    job_id = event['args']['jobId']
    
    # Fetch job to get delivery info
    job_state, bids = contracts.order_book.functions.getJob(job_id).call()
    
    # Get delivery URI from NeoFS (stored by agent)
    # In production, agent would emit custom event with URI
    # Or store in a separate registry
    
    # Download results
    results = await neofs_client.download_json(delivery_uri)
    
    # Format and return to user
    response = format_results_for_user(results)
    return response
```

## Implementation

### Add NeoFS Upload to Butler API

```python
# In spoonos_butler_api.py
from agents.src.shared.neofs import NeoFSClient, NeoFSConfig, ObjectAttribute

# Initialize on startup
neofs_client = NeoFSClient(NeoFSConfig(
    gateway_url=os.getenv("NEOFS_GATEWAY_URL"),
    container_id=os.getenv("NEOFS_CONTAINER_ID")
))

# In quote endpoint
@app.post("/api/spoonos/quote")
async def get_quote(request: QuoteRequest):
    # Upload job details
    job_details = {
        "description": request.description,
        "tags": request.tags,
        "requirements": request.requirements,  # Add this to request model
        "timestamp": int(time.time())
    }
    
    result = await neofs_client.upload_json(job_details, attributes=[
        ObjectAttribute(key="type", value="job_metadata")
    ])
    
    metadata_uri = f"neofs://{result.container_id}/{result.object_id}"
    
    # Post job with metadata URI
    job_id = post_job(
        contracts,
        description=request.description,
        metadata_uri=metadata_uri,
        tags=request.tags,
        deadline=int(time.time()) + request.deadline
    )
    # ... rest of code
```

## Environment Variables

Add to `agents/.env`:
```env
# NeoFS Storage
NEOFS_GATEWAY_URL=https://rest.testnet.fs.neo.org
NEOFS_CONTAINER_ID=9iMKzkCQ7TftU6VVKdVGKJiNq3dsY2K8UoFKWzR53ieK
```

## Cost & Limits

- **Testnet**: Free, unlimited storage (for testing only)
- **Mainnet**: Pay once per object with GAS, no recurring fees
- **Object Size**: Up to 64MB per object
- **Throughput**: Suitable for job metadata and results (not large video files)

## Next Steps

1. Test NeoFS connection: `python agents/test_neofs.py`
2. Update Butler API to upload job metadata
3. Update Worker agents to upload delivery results
4. Add NeoFS URIs to contract events/logs for easy retrieval
