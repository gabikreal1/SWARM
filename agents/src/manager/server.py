"""
Manager Agent A2A Server

FastAPI server exposing A2A endpoints for the Manager Agent.
The Manager orchestrates jobs and coordinates workers.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ..shared.a2a import (
    A2AMessage,
    A2AResponse,
    A2AMethod,
    A2AErrorCode,
    verify_message,
    is_message_fresh,
    create_error_response,
    create_success_response,
)

from .agent import ManagerAgent, create_manager_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==============================================================================
# GLOBAL STATE
# ==============================================================================

agent: Optional[ManagerAgent] = None


# ==============================================================================
# LIFESPAN MANAGEMENT
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initialize and cleanup resources"""
    global agent
    
    logger.info("🚀 Starting Archive Manager Agent Server...")
    
    # Initialize the Manager Agent
    try:
        agent = await create_manager_agent()
        await agent.start()
        logger.info("✅ Manager Agent initialized and running")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Manager Agent: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("👋 Shutting down Manager Agent...")
    if agent:
        await agent.stop()
    logger.info("Manager Agent stopped")


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="Archive Manager Agent",
    description="Job orchestration agent for Archive Protocol on NeoX",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class JobRequest(BaseModel):
    """Request to process a new job"""
    description: str
    job_type: Optional[int] = None
    budget: Optional[int] = None


class StatusResponse(BaseModel):
    """Agent status response"""
    status: str
    agent: str
    wallet_address: Optional[str] = None
    tracked_jobs: int = 0
    event_listener_running: bool = False


# ==============================================================================
# A2A ENDPOINTS
# ==============================================================================

@app.post("/v1/rpc", response_model=A2AResponse)
async def handle_a2a_request(request: Request):
    """
    Main A2A RPC endpoint.
    
    Handles incoming A2A messages from:
    - Worker agents submitting results
    - Other managers coordinating
    - External clients
    """
    global agent
    
    try:
        body = await request.json()
        message = A2AMessage(**body)
    except Exception as e:
        return create_error_response(
            0,
            A2AErrorCode.PARSE_ERROR,
            f"Invalid request: {e}"
        )
    
    # Verify signature if present
    if message.signature:
        is_valid, signer = verify_message(message)
        if not is_valid:
            return create_error_response(
                message.id,
                A2AErrorCode.SIGNATURE_INVALID,
                "Invalid message signature"
            )
        
        # Check message freshness
        if not is_message_fresh(message):
            return create_error_response(
                message.id,
                A2AErrorCode.MESSAGE_EXPIRED,
                "Message has expired"
            )
    
    # Route to appropriate handler
    if message.method == A2AMethod.PING.value:
        return create_success_response(message.id, {
            "status": "ok",
            "agent": "manager"
        })
    
    elif message.method == A2AMethod.GET_CAPABILITIES.value:
        return create_success_response(message.id, {
            "agent": "archive_manager",
            "role": "orchestrator",
            "capabilities": [
                "job_decomposition",
                "bid_management",
                "worker_coordination",
                "delivery_approval"
            ],
            "supported_job_types": [
                "TIKTOK_SCRAPE",
                "WEB_SCRAPE",
                "CALL_VERIFICATION",
                "DATA_ANALYSIS",
                "COMPOSITE"
            ]
        })
    
    elif message.method == A2AMethod.GET_STATUS.value:
        return create_success_response(message.id, {
            "status": "active",
            "wallet_address": agent.wallet.address if agent and agent.wallet else None,
            "tracked_jobs": len(agent.tracked_jobs) if agent else 0,
            "event_listener_running": agent._running if agent else False
        })
    
    elif message.method == A2AMethod.SUBMIT_RESULT.value:
        # Handle result submission from worker agents
        return await handle_result_submission(message)
    
    elif message.method == "process_request":
        # Handle job processing request
        return await handle_process_request(message)
    
    else:
        return create_error_response(
            message.id,
            A2AErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {message.method}"
        )


async def handle_result_submission(message: A2AMessage) -> A2AResponse:
    """Handle task result submission from worker agents"""
    global agent
    
    params = message.params
    job_id = params.get("job_id")
    task_type = params.get("task_type")
    result_uri = params.get("result_uri")
    status = params.get("status")
    
    logger.info(f"📥 Result received for job {job_id}: {status}")
    logger.info(f"   Task type: {task_type}, Result URI: {result_uri}")
    
    # Track the delivery
    if agent and job_id in agent.tracked_jobs:
        job = agent.tracked_jobs[job_id]
        job.deliveries.append({
            "task_type": task_type,
            "result_uri": result_uri,
            "status": status
        })
        
        # Trigger delivery review via the agent
        asyncio.create_task(agent._review_delivery_manual(job_id, result_uri))
    
    return create_success_response(message.id, {
        "acknowledged": True,
        "job_id": job_id
    })


async def handle_process_request(message: A2AMessage) -> A2AResponse:
    """Handle a request to process a new job"""
    global agent
    
    if not agent:
        return create_error_response(
            message.id,
            A2AErrorCode.INTERNAL_ERROR,
            "Agent not initialized"
        )
    
    request_text = message.params.get("request", "")
    if not request_text:
        return create_error_response(
            message.id,
            A2AErrorCode.INVALID_PARAMS,
            "Missing 'request' parameter"
        )
    
    try:
        response = await agent.process_request(request_text)
        return create_success_response(message.id, {
            "response": response
        })
    except Exception as e:
        return create_error_response(
            message.id,
            A2AErrorCode.INTERNAL_ERROR,
            str(e)
        )


# ==============================================================================
# REST ENDPOINTS
# ==============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "manager"
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get detailed agent status"""
    global agent
    
    return StatusResponse(
        status="active" if agent and agent._running else "stopped",
        agent="manager",
        wallet_address=agent.wallet.address if agent and agent.wallet else None,
        tracked_jobs=len(agent.tracked_jobs) if agent else 0,
        event_listener_running=agent._running if agent else False
    )


@app.get("/jobs")
async def list_jobs():
    """List all tracked jobs"""
    global agent
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return {
        "jobs": agent.get_tracked_jobs()
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: int):
    """Get details of a specific job"""
    global agent
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if job_id not in agent.tracked_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = agent.tracked_jobs[job_id]
    return {
        "job_id": job_id,
        "description": job.description,
        "job_type": job.job_type,
        "budget": job.budget,
        "status": job.status,
        "sub_tasks": job.sub_tasks,
        "accepted_bids": job.accepted_bids,
        "deliveries": job.deliveries
    }


@app.post("/process")
async def process_job(request: JobRequest):
    """
    Process a new job request.
    
    This is a convenience endpoint for submitting jobs to be orchestrated.
    """
    global agent
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    prompt = f"Process this job request: {request.description}"
    
    if request.job_type is not None:
        prompt += f"\nJob type: {request.job_type}"
    if request.budget is not None:
        prompt += f"\nBudget: {request.budget} USDC micro-units"
    
    try:
        response = await agent.process_request(prompt)
        return {
            "success": True,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error processing job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wallet")
async def get_wallet_info():
    """Get wallet information"""
    global agent
    
    if not agent or not agent.wallet:
        raise HTTPException(status_code=503, detail="Wallet not configured")
    
    balance = agent.wallet.get_balance()
    return {
        "address": agent.wallet.address,
        "balance": {
            "native": str(balance.native),
            "usdc": str(balance.usdc)
        }
    }


# ==============================================================================
# SERVER RUNNER
# ==============================================================================

def run_server():
    """Run the Manager Agent server"""
    port = int(os.getenv("MANAGER_PORT", "3001"))
    host = os.getenv("MANAGER_HOST", "0.0.0.0")
    
    logger.info(f"Starting Manager Agent server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
