"""
SpoonOS Butler API Bridge
Exposes HTTP endpoints that the ElevenLabs voice agent calls via client tools.
"""
import os
import sys
import time
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv

# Add SWARM root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.src.shared.slot_questioning import SlotFiller
from agents.src.shared.contracts import (
    get_contracts,
    approve_usdc,
    post_job,
    get_bids_for_job,
    accept_bid,
    ContractInstances,
)
from agents.neofs_helper import upload_job_metadata
from qdrant_client import QdrantClient
from mem0 import MemoryClient

load_dotenv()

app = FastAPI(title="Spoonos Butler API Bridge")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals
contracts: Optional[ContractInstances] = None
slot_filler: Optional[SlotFiller] = None
qdrant_client: Optional[QdrantClient] = None
mem0_client: Optional[MemoryClient] = None


class InquireRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"


class QuoteRequest(BaseModel):
    description: str
    tags: List[str]
    deadline: int = 3600


class ConfirmRequest(BaseModel):
    jobId: int
    bidId: int


@app.on_event("startup")
async def startup_event():
    """Initialize blockchain, slot filler, and memory clients."""
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

            # Auto-approve USDC for Escrow if needed
            if contracts.account:
                escrow_address = contracts.escrow.address
                allowance = contracts.usdc.functions.allowance(
                    contracts.account.address, escrow_address
                ).call()
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


@app.get("/")
async def root():
    return {"status": "Spoonos Butler API is running"}


@app.post("/api/spoonos/inquire")
async def inquire(request: InquireRequest):
    """RAG + slot filling to understand user intent."""
    print(f"📥 Inquire: {request.query}")

    # Candidate tools (job types) we support
    candidate_tools = [
        {
            "name": "tiktok_scrape",
            "description": "Scrape TikTok posts from a user",
            "required_params": ["username", "count"],
        },
        {
            "name": "web_scrape",
            "description": "Scrape a website",
            "required_params": ["url"],
        },
    ]

    # Simple heuristic extraction (replace with LLM extraction if desired)
    current_slots = {}
    if "tiktok" in request.query.lower():
        if "@" in request.query:
            current_slots["username"] = request.query.split("@")[1].split()[0]
        if "posts" in request.query:
            import re

            nums = re.findall(r"\d+", request.query)
            if nums:
                current_slots["count"] = nums[0]

    try:
        if slot_filler:
            missing_slots, questions, chosen_tool = slot_filler.fill(
                user_message=request.query,
                current_slots=current_slots,
                candidate_tools=candidate_tools,
            )
        else:
            missing_slots, questions, chosen_tool = [], [], "tiktok_scrape"

        if missing_slots:
            return {
                "status": "question",
                "text": questions[0] if questions else f"I need {missing_slots[0]}",
                "missing_slots": missing_slots,
                "tool": chosen_tool,
            }

        return {
            "status": "ready",
            "text": f"I have all details for {chosen_tool}. Shall I get a quote?",
            "slots": current_slots,
            "tool": chosen_tool,
            "description": f"{chosen_tool} for {current_slots}",
            "tags": [chosen_tool],
        }

    except Exception as e:
        print(f"Error in inquire: {e}")
        return {"status": "error", "text": "I'm having trouble understanding. Could you repeat?"}


@app.post("/api/spoonos/quote")
async def get_quote(request: QuoteRequest):
    """Post job with NeoFS metadata, wait, and poll bids."""
    print(f"📥 Quote Request: {request.description}")
    if not contracts:
        raise HTTPException(503, "Blockchain not connected")

    # 1) Upload job metadata to NeoFS
    print("📤 Uploading job metadata to NeoFS...")
    try:
        result = upload_job_metadata(
            tool=request.tags[0] if request.tags else "unknown",
            parameters={"description": request.description},
            poster=contracts.account.address,
            requirements={"deadline": request.deadline},
        )
        if not result:
            raise HTTPException(500, "Failed to upload metadata to NeoFS")
        object_id, metadata_uri = result
        print(f"✅ Metadata uploaded: {metadata_uri}")
    except Exception as e:
        print(f"❌ NeoFS Upload Failed: {e}")
        raise HTTPException(500, f"Failed to upload metadata: {e}")

    # 2) Post job to blockchain
    try:
        job_id = post_job(
            contracts,
            description=request.description,
            metadata_uri=metadata_uri,
            tags=request.tags,
            deadline=int(time.time()) + request.deadline,
        )
        print(f"✅ Job Posted: {job_id}")
    except Exception as e:
        print(f"❌ Post Job Failed: {e}")
        raise HTTPException(500, f"Failed to post job: {e}")

    # 3) Wait briefly for bids
    print("⏳ Waiting for bids (8s)...")
    await asyncio.sleep(8)

    # 4) Poll bids
    try:
        bids = get_bids_for_job(contracts, job_id)
        print(f"🔎 Found {len(bids)} bids")

        valid_bids = []
        for bid in bids:
            # Bid: (id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt)
            valid_bids.append(
                {
                    "id": bid[0],
                    "price": bid[3],
                    "bidder": bid[2],
                    "reputation": bid[5],
                }
            )

        if not valid_bids:
            return {
                "status": "no_bids",
                "text": "No agents responded yet. I'll keep checking.",
                "jobId": job_id,
            }

        best_bid = sorted(valid_bids, key=lambda x: x["price"])[0]
        return {
            "status": "quoted",
            "text": f"Best offer is {best_bid['price']} USDC. Shall I confirm?",
            "jobId": job_id,
            "bidId": best_bid["id"],
            "price": best_bid["price"],
            "agent": best_bid["bidder"],
        }

    except Exception as e:
        print(f"❌ Fetch Bids Failed: {e}")
        raise HTTPException(500, f"Failed to fetch bids: {e}")


@app.post("/api/spoonos/confirm")
async def confirm_bid(request: ConfirmRequest):
    """Accept a bid and lock funds in escrow."""
    print(f"📥 Confirm Bid: Job {request.jobId}, Bid {request.bidId}")
    if not contracts:
        raise HTTPException(503, "Blockchain not connected")

    try:
        tx = accept_bid(
            contracts,
            job_id=request.jobId,
            bid_id=request.bidId,
            response_uri="ipfs://response",
        )
        print(f"✅ Bid Accepted: {tx}")
        return {
            "status": "success",
            "text": "Bid accepted. Funds locked in escrow.",
            "tx": tx,
        }
    except Exception as e:
        print(f"❌ Accept Bid Failed: {e}")
        raise HTTPException(500, f"Failed to accept bid: {e}")


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Spoonos Butler API Bridge...")
    print("📍 Listening on http://localhost:3001")
    uvicorn.run(app, host="0.0.0.0", port=3001)
