"""
Spoonos Butler API Bridge
Exposes HTTP endpoints that the ElevenLabs voice agent calls via client tools
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
import os

# Add the agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# Import your Spoonos agent (adjust imports based on your structure)
# from agents.src.manager.agent import ManagerAgent

app = FastAPI(title="Spoonos Butler API Bridge")

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class QueryRequest(BaseModel):
    query: str
    timestamp: Optional[int] = None

class JobFilters(BaseModel):
    filters: Optional[Dict[str, Any]] = None

class JobApplication(BaseModel):
    jobId: str
    agentId: str

# Initialize your Spoonos Butler agent
# butler_agent = ManagerAgent(config)  # Your actual agent initialization

@app.get("/")
async def root():
    return {"status": "Spoonos Butler API is running"}

@app.post("/api/spoonos")
async def query_butler(request: QueryRequest):
    """
    General query endpoint - forwards any question to Spoonos Butler
    This is the main bridge between ElevenLabs and your AI agent
    """
    try:
        print(f"📥 Received query: {request.query}")
        
        # TODO: Replace with your actual Spoonos agent call
        # response = await butler_agent.process_query(request.query)
        
        # Mock response for now
        response = f"Butler received your query: '{request.query}'. This would normally be processed by your Spoonos agent."
        
        print(f"📤 Sending response: {response}")
        
        return {
            "response": response,
            "timestamp": request.timestamp
        }
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spoonos/jobs")
async def get_jobs(request: JobFilters):
    """
    Get job listings from JobRegistry contract
    """
    try:
        print(f"📥 Fetching jobs with filters: {request.filters}")
        
        # TODO: Query your JobRegistry smart contract
        # jobs = await job_registry.get_jobs(filters=request.filters)
        
        # Mock response
        jobs = [
            {
                "id": "1",
                "title": "Scrape restaurant data from Google Maps",
                "reward": 100,
                "category": "web_scraping",
                "status": "open"
            },
            {
                "id": "2", 
                "title": "Analyze sentiment in social media posts",
                "reward": 150,
                "category": "data_analysis",
                "status": "open"
            },
            {
                "id": "3",
                "title": "Integrate payment API with mobile app",
                "reward": 200,
                "category": "api_integration", 
                "status": "open"
            }
        ]
        
        # Apply filters if provided
        if request.filters:
            if "min_reward" in request.filters:
                jobs = [j for j in jobs if j["reward"] >= request.filters["min_reward"]]
            if "category" in request.filters:
                jobs = [j for j in jobs if j["category"] == request.filters["category"]]
        
        print(f"📤 Returning {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/spoonos/jobs/apply")
async def apply_to_job(application: JobApplication):
    """
    Submit job application via smart contract
    """
    try:
        print(f"📥 Application: Agent {application.agentId} → Job {application.jobId}")
        
        # TODO: Call your smart contract to submit application
        # tx = await job_registry.apply_to_job(
        #     job_id=application.jobId,
        #     agent_id=application.agentId
        # )
        
        # Mock response
        mock_tx_hash = f"0x{''.join([hex(ord(c))[2:] for c in application.jobId[:8]])}"
        
        print(f"✅ Application submitted: {mock_tx_hash}")
        
        return {
            "success": True,
            "txHash": mock_tx_hash,
            "message": f"Successfully applied to job {application.jobId}"
        }
        
    except Exception as e:
        print(f"❌ Error submitting application: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/spoonos/wallet/{address}")
async def get_wallet_status(address: str):
    """
    Check wallet balance and active jobs
    """
    try:
        print(f"📥 Checking wallet: {address}")
        
        # TODO: Query blockchain for wallet info
        # balance = await get_token_balance(address)
        # active_jobs = await get_active_jobs_for_agent(address)
        
        # Mock response
        wallet_info = {
            "address": address,
            "balance": 1500,  # tokens
            "activeJobs": 2,
            "completedJobs": 15,
            "reputation": 4.8
        }
        
        print(f"📤 Wallet info: {wallet_info}")
        return wallet_info
        
    except Exception as e:
        print(f"❌ Error checking wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Spoonos Butler API Bridge...")
    print("📍 Listening on http://localhost:3001")
    print("🔗 Frontend should set: NEXT_PUBLIC_SPOONOS_BUTLER_URL=http://localhost:3001/api/spoonos")
    uvicorn.run(app, host="0.0.0.0", port=3001)
