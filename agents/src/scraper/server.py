"""
Scraper Agent Server

FastAPI server that:
1. Exposes A2A endpoints for agent communication
2. Runs the event listener for blockchain events
3. Provides health/status endpoints
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
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

from .agent import ScraperAgent, create_scraper_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: ScraperAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global agent
    
    logger.info("🕷️ Starting Archive Scraper Agent...")
    
    # Initialize and start agent
    agent = await create_scraper_agent()
    await agent.start()
    
    yield
    
    # Cleanup
    if agent:
        agent.stop()
    logger.info("👋 Scraper Agent stopped")


app = FastAPI(
    title="Archive Scraper Agent",
    description="TikTok and web scraping agent for Archive Protocol",
    version="0.1.0",
    lifespan=lifespan
)


# Health & Status Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "scraper"}


@app.get("/status")
async def get_status():
    """Get agent status"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent.get_status()


@app.get("/wallet")
async def get_wallet_info():
    """Get wallet information"""
    if not agent or not agent.wallet:
        raise HTTPException(status_code=503, detail="Wallet not configured")
    
    balance = agent.wallet.get_balance()
    return {
        "address": agent.wallet.address,
        "native_balance": str(balance.native),
        "usdc_balance": str(balance.usdc),
    }


@app.get("/jobs")
async def get_active_jobs():
    """Get active jobs"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return {
        "active_jobs": [
            {
                "job_id": job.job_id,
                "status": job.status,
                "job_type": job.job_type,
            }
            for job in agent.active_jobs.values()
        ]
    }


# A2A Endpoint

@app.post("/v1/rpc", response_model=A2AResponse)
async def handle_a2a_request(request: Request):
    """
    Main A2A RPC endpoint.
    
    Handles incoming A2A messages from the Manager Agent.
    """
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
        return create_success_response(message.id, {"status": "ok", "agent": "scraper"})
    
    elif message.method == A2AMethod.GET_CAPABILITIES.value:
        caps = agent.get_status() if agent else {}
        return create_success_response(message.id, {
            "agent": "archive_scraper",
            "capabilities": caps.get("capabilities", []),
            "supported_job_types": caps.get("supported_job_types", []),
        })
    
    elif message.method == A2AMethod.GET_STATUS.value:
        return create_success_response(message.id, agent.get_status() if agent else {})
    
    elif message.method == A2AMethod.EXECUTE_TASK.value:
        return await handle_task_execution(message)
    
    else:
        return create_error_response(
            message.id,
            A2AErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {message.method}"
        )


async def handle_task_execution(message: A2AMessage) -> A2AResponse:
    """Handle task execution requests from Manager Agent"""
    global agent
    
    if not agent:
        return create_error_response(
            message.id,
            A2AErrorCode.INTERNAL_ERROR,
            "Agent not initialized"
        )
    
    params = message.params
    job_id = params.get("job_id")
    task_type = params.get("task_type")
    description = params.get("description", "")
    
    logger.info(f"📥 Received task: job_id={job_id}, type={task_type}")
    
    # Return acceptance - job will be executed via event listener
    return create_success_response(message.id, {
        "accepted": True,
        "job_id": job_id,
        "status": "queued"
    })


# Manual test endpoints

@app.post("/scrape/tiktok")
async def manual_tiktok_scrape(query: str, max_results: int = 10):
    """Manual TikTok scrape endpoint for testing"""
    if not agent or not agent.llm_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    prompt = f"Scrape TikTok for: {query}. Return top {max_results} results."
    response = await agent.llm_agent.run(prompt)
    return {"response": response}


@app.post("/scrape/web")
async def manual_web_scrape(url: str):
    """Manual web scrape endpoint for testing"""
    if not agent or not agent.llm_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    prompt = f"Scrape this website: {url}"
    response = await agent.llm_agent.run(prompt)
    return {"response": response}


def run_server():
    """Run the Scraper Agent server"""
    port = int(os.getenv("SCRAPER_PORT", "3002"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_server()

