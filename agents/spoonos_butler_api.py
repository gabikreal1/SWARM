"""
SpoonOS Butler API Bridge
Exposes HTTP endpoints that the ElevenLabs voice agent calls via client tools.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sys
import os
import time
import asyncio
import json
from dotenv import load_dotenv

<<<<<<< Updated upstream
# Add the agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

# Import your SpoonOS agent (adjust imports based on your structure)
# from agents.src.manager.agent import ManagerAgent
=======
# Add SWARM root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.src.shared.slot_questioning import SlotFiller
from agents.src.shared.contracts import get_contracts, approve_usdc, post_job, get_bids_for_job, accept_bid, ContractInstances
from neofs_helper import upload_job_metadata
from qdrant_client import QdrantClient
from mem0 import MemoryClient
from web3 import Web3

load_dotenv()
>>>>>>> Stashed changes

app = FastAPI(title="Spoonos Butler API Bridge")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< Updated upstream

# Request models
class QueryRequest(BaseModel):
=======
# Globals
contracts: Optional[ContractInstances] = None
slot_filler: Optional[SlotFiller] = None
qdrant_client: Optional[QdrantClient] = None
mem0_client: Optional[MemoryClient] = None

# Request Models
class InquireRequest(BaseModel):
>>>>>>> Stashed changes
    query: str
    user_id: Optional[str] = "default_user"

<<<<<<< Updated upstream

class JobFilters(BaseModel):
    filters: Optional[Dict[str, Any]] = None


class JobApplication(BaseModel):
    jobId: str
    agentId: str


# Initialize your Spoonos Butler agent
# butler_agent = ManagerAgent(config)  # Your actual agent initialization
=======
class QuoteRequest(BaseModel):
    description: str
    tags: List[str]
    deadline: int = 3600

class ConfirmRequest(BaseModel):
    jobId: int
    bidId: int

@app.on_event("startup")
async def startup_event():
    global contracts, slot_filler, qdrant_client, mem0_client
    
    print("🚀 Starting Spoonos Butler API...")
    
    # Initialize Contracts
    private_key = os.getenv("NEOX_PRIVATE_KEY")
    if not private_key:
        print("⚠️ NEOX_PRIVATE_KEY not found. Blockchain features will fail.")
    else:
        try:
            contracts = get_contracts(private_key)
            print("✅ Connected to NeoX Blockchain")
            
            # Auto-approve USDC
            if contracts.account:
                usdc_address = contracts.usdc.address
                escrow_address = contracts.escrow.address
                allowance = contracts.usdc.functions.allowance(contracts.account.address, escrow_address).call()
                if allowance < 1000 * 10**6:
                    print("🔄 Approving USDC for Escrow...")
                    approve_usdc(contracts, escrow_address, 2**256 - 1)
                    print("✅ USDC Approved")
        except Exception as e:
            print(f"❌ Failed to connect to blockchain: {e}")

    # Initialize AI Components
    try:
        slot_filler = SlotFiller(user_id="butler_api_user")
        print("✅ SlotFiller Initialized")
    except Exception as e:
        print(f"⚠️ SlotFiller init failed: {e}")

    # Initialize Clients
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
>>>>>>> Stashed changes


@app.get("/")
async def root():
    return {"status": "Spoonos Butler API is running"}

<<<<<<< Updated upstream

@app.post("/api/spoonos")
async def query_butler(request: QueryRequest):
    """
    General query endpoint - forwards any question to Spoonos Butler.
    """
    try:
        print(f"Received query: {request.query}")

        # TODO: Replace with your actual Spoonos agent call
        # response = await butler_agent.process_query(request.query)

        # Mock response for now
        response = f"Butler received your query: '{request.query}'. This would normally be processed by your Spoonos agent."

        print(f"Sending response: {response}")

        return {
            "response": response,
            "timestamp": request.timestamp,
        }
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/spoonos/jobs")
async def get_jobs(request: JobFilters):
    """
    Get job listings from JobRegistry contract.
    """
    try:
        print(f"Fetching jobs with filters: {request.filters}")

        # TODO: Query your JobRegistry smart contract
        # jobs = await job_registry.get_jobs(filters=request.filters)

        # Mock response
        jobs = [
            {
                "id": "1",
                "title": "Scrape restaurant data from Google Maps",
                "reward": 100,
                "category": "web_scraping",
                "status": "open",
            },
            {
                "id": "2",
                "title": "Analyze sentiment in social media posts",
                "reward": 150,
                "category": "data_analysis",
                "status": "open",
            },
            {
                "id": "3",
                "title": "Integrate payment API with mobile app",
                "reward": 200,
                "category": "api_integration",
                "status": "open",
            },
        ]

        # Apply filters if provided
        if request.filters:
            if "min_reward" in request.filters:
                jobs = [j for j in jobs if j["reward"] >= request.filters["min_reward"]]
            if "category" in request.filters:
                jobs = [j for j in jobs if j["category"] == request.filters["category"]]

        print(f"Returning {len(jobs)} jobs")
        return jobs

    except Exception as e:
        print(f"Error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/spoonos/jobs/apply")
async def apply_to_job(application: JobApplication):
    """
    Submit job application via smart contract.
=======
@app.post("/api/spoonos/inquire")
async def inquire(request: InquireRequest):
    """
    RAG + Slot Filling to understand user intent.
    """
    print(f"📥 Inquire: {request.query}")
    
    # Define candidate tools (jobs we can do)
    candidate_tools = [
        {
            "name": "tiktok_scrape",
            "description": "Scrape TikTok posts from a user",
            "required_params": ["username", "count"]
        },
        {
            "name": "web_scrape",
            "description": "Scrape a website",
            "required_params": ["url"]
        }
    ]
    
    # Mock extraction (In production, use LLM to extract slots from query)
    current_slots = {}
    if "tiktok" in request.query.lower():
        if "@" in request.query:
            current_slots["username"] = request.query.split("@")[1].split()[0]
        if "posts" in request.query:
            import re
            nums = re.findall(r'\d+', request.query)
            if nums:
                current_slots["count"] = nums[0]
    
    try:
        if slot_filler:
            missing_slots, questions, chosen_tool = slot_filler.fill(
                user_message=request.query,
                current_slots=current_slots,
                candidate_tools=candidate_tools
            )
        else:
            # Fallback if slot_filler failed init
            missing_slots = []
            questions = []
            chosen_tool = "tiktok_scrape"

        if missing_slots:
            return {
                "status": "question",
                "text": questions[0] if questions else f"I need {missing_slots[0]}",
                "missing_slots": missing_slots,
                "tool": chosen_tool
            }
        else:
            return {
                "status": "ready",
                "text": f"I have all details for {chosen_tool}. Shall I get a quote?",
                "slots": current_slots,
                "tool": chosen_tool,
                "description": f"{chosen_tool} for {current_slots}",
                "tags": [chosen_tool]
            }
            
    except Exception as e:
        print(f"Error in inquire: {e}")
        return {"status": "error", "text": "I'm having trouble understanding. Could you repeat?"}

@app.post("/api/spoonos/quote")
async def get_quote(request: QuoteRequest):
    """
    Post job with NeoFS metadata, wait, poll bids.
>>>>>>> Stashed changes
    """
    print(f"📥 Quote Request: {request.description}")
    if not contracts:
        raise HTTPException(503, "Blockchain not connected")
        
    # 1. Upload job metadata to NeoFS
    print("📤 Uploading job metadata to NeoFS...")
    try:
<<<<<<< Updated upstream
        print(f"Application: Agent {application.agentId} -> Job {application.jobId}")

        # TODO: Call your smart contract to submit application
        # tx = await job_registry.apply_to_job(
        #     job_id=application.jobId,
        #     agent_id=application.agentId
        # )

        # Mock response
        mock_tx_hash = f"0x{''.join([hex(ord(c))[2:] for c in application.jobId[:8]])}"

        print(f"Application submitted: {mock_tx_hash}")

        return {
            "success": True,
            "txHash": mock_tx_hash,
            "message": f"Successfully applied to job {application.jobId}",
=======
        result = upload_job_metadata(
            tool=request.tags[0] if request.tags else "unknown",
            parameters={"description": request.description},
            poster=contracts.account.address,
            requirements={"deadline": request.deadline}
        )
        
        if not result:
            raise HTTPException(500, "Failed to upload metadata to NeoFS")
            
        object_id, metadata_uri = result
        print(f"✅ Metadata uploaded: {metadata_uri}")
    except Exception as e:
        print(f"❌ NeoFS Upload Failed: {e}")
        raise HTTPException(500, f"Failed to upload metadata: {e}")
        
    # 2. Post Job to blockchain
    try:
        job_id = post_job(
            contracts,
            description=request.description,
            metadata_uri=metadata_uri,
            tags=request.tags,
            deadline=int(time.time()) + request.deadline
        )
        print(f"✅ Job Posted: {job_id}")
    except Exception as e:
        print(f"❌ Post Job Failed: {e}")
        raise HTTPException(500, f"Failed to post job: {e}")
        
    # 2. Wait for Bids
    print("⏳ Waiting for bids (8s)...")
    await asyncio.sleep(8)
    
    # 3. Poll Bids
    try:
        bids = get_bids_for_job(contracts, job_id)
        print(f"🔎 Found {len(bids)} bids")
        
        valid_bids = []
        for bid in bids:
            # Bid struct: (id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt)
            valid_bids.append({
                "id": bid[0],
                "price": bid[3],
                "bidder": bid[2],
                "reputation": bid[5]
            })
            
        if not valid_bids:
            return {
                "status": "no_bids",
                "text": "No agents responded yet. I'll keep checking.",
                "jobId": job_id
            }
            
        # Sort by price (asc)
        best_bid = sorted(valid_bids, key=lambda x: x['price'])[0]
        
        return {
            "status": "quoted",
            "text": f"Best offer is {best_bid['price']} USDC. Shall I confirm?",
            "jobId": job_id,
            "bidId": best_bid['id'],
            "price": best_bid['price'],
            "agent": best_bid['bidder']
>>>>>>> Stashed changes
        }

    except Exception as e:
<<<<<<< Updated upstream
        print(f"Error submitting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spoonos/wallet/{address}")
async def get_wallet_status(address: str):
    """
    Check wallet balance and active jobs.
    """
    try:
        print(f"Checking wallet: {address}")

        # TODO: Query blockchain for wallet info
        # balance = await get_token_balance(address)
        # active_jobs = await get_active_jobs_for_agent(address)

        # Mock response
        wallet_info = {
            "address": address,
            "balance": 1500,  # tokens
            "activeJobs": 2,
            "completedJobs": 15,
            "reputation": 4.8,
        }

        print(f"Wallet info: {wallet_info}")
        return wallet_info

    except Exception as e:
        print(f"Error checking wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))
=======
        print(f"❌ Fetch Bids Failed: {e}")
        raise HTTPException(500, f"Failed to fetch bids: {e}")

@app.post("/api/spoonos/confirm")
async def confirm_bid(request: ConfirmRequest):
    print(f"📥 Confirm Bid: Job {request.jobId}, Bid {request.bidId}")
    if not contracts:
        raise HTTPException(503, "Blockchain not connected")
        
    try:
        tx = accept_bid(
            contracts,
            job_id=request.jobId,
            bid_id=request.bidId,
            response_uri="ipfs://response"
        )
        print(f"✅ Bid Accepted: {tx}")
        return {
            "status": "success",
            "text": "Bid accepted. Funds locked in escrow.",
            "tx": tx
        }
    except Exception as e:
        print(f"❌ Accept Bid Failed: {e}")
        raise HTTPException(500, f"Failed to accept bid: {e}")
>>>>>>> Stashed changes


if __name__ == "__main__":
    import uvicorn
<<<<<<< Updated upstream

    print("Starting Spoonos Butler API Bridge...")
    print("Listening on http://localhost:3001")
    print("Frontend should set: NEXT_PUBLIC_SPOONOS_BUTLER_URL=http://localhost:3001/api/spoonos")
=======
    print("🚀 Starting Spoonos Butler API Bridge...")
    print("📍 Listening on http://localhost:3001")
>>>>>>> Stashed changes
    uvicorn.run(app, host="0.0.0.0", port=3001)
