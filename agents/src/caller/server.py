"""
Caller Agent Server

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
import httpx

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

from .agent import CallerAgent, create_caller_agent
from ..shared.neofs import get_neofs_client
from ..shared import neofs as neofs_module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: CallerAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global agent
    
    logger.info("📞 Starting Archive Caller Agent...")
    
    # Initialize and start agent
    agent = await create_caller_agent()
    await agent.start()
    
    yield
    
    # Cleanup
    if agent:
        agent.stop()
    logger.info("👋 Caller Agent stopped")


app = FastAPI(
    title="Archive Caller Agent",
    description="Phone verification agent for Archive Protocol",
    version="0.1.0",
    lifespan=lifespan
)


# Health & Status Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "caller"}


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


# ElevenLabs webhook endpoint (post-call/status)
@app.post("/webhooks/elevenlabs")
async def elevenlabs_webhook(request: Request):
    """
    Receive ElevenLabs ConvAI/Twilio webhook callbacks.
    Validates the shared secret if provided, extracts summary info,
    uploads it to NeoFS, and returns the NeoFS URI.
    """
    secret_expected = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
    provided = request.headers.get("x-elevenlabs-signature") or request.headers.get("x-webhook-secret")

    # Validate secret if configured
    if secret_expected and provided != secret_expected:
        logger.warning("❌ ElevenLabs webhook: invalid secret")
        raise HTTPException(status_code=401, detail="invalid secret")

    try:
        payload = await request.json()
    except Exception:
        payload = {"error": "invalid json"}

    logger.info(f"📨 ElevenLabs webhook payload: {payload}")

    # Extract known fields but keep full payload intact
    conversation_id = payload.get("conversation_id") or payload.get("conversationId")
    call_sid = payload.get("callSid") or payload.get("call_sid")
    status = payload.get("status") or payload.get("call_status")
    summary = payload.get("summary") or payload.get("analysis") or payload.get("transcript")
    to_number = payload.get("to") or payload.get("to_number") or ""
    job_id = payload.get("jobId") or payload.get("job_id") or "unknown"

    # Prepare call result doc (will be stored to NeoFS; keep original payload untouched)
    call_result = {
        "conversation_id": conversation_id,
        "callSid": call_sid,
        "status": status,
        "summary": summary,
        "to": to_number,
        "job_id": job_id,
        "received_at": __import__("datetime").datetime.utcnow().isoformat(),
        "payload": payload,
    }

    neofs_uri = None
    try:
        client = get_neofs_client()
        upload = await client.upload_call_result(
            call_result,
            job_id=str(job_id),
            phone_number=to_number or "unknown",
        )
        await client.close()
        neofs_uri = f"neofs://{upload.container_id}/{upload.object_id}"
    except Exception as e:
        logger.warning(f"⚠️ Failed to upload call summary to NeoFS: {e}")

    # Optionally persist to web app DB via API if configured
    calls_api = os.getenv("CALL_SUMMARY_WEBHOOK_URL")
    call_summary_secret = os.getenv("CALL_SUMMARY_SECRET") or secret_expected
    if calls_api:
        try:
            # Add neofs_uri into the payload we forward, so DB has full content + archival pointer
            payload_with_neofs = dict(payload)
            payload_with_neofs["neofs_uri"] = neofs_uri

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    calls_api,
                    json={
                        "conversationId": conversation_id,
                        "callSid": call_sid,
                        "status": status,
                        "summary": summary,
                        "toNumber": to_number,
                        "jobId": str(job_id),
                        "neofsUri": neofs_uri,
                        "payload": payload_with_neofs,
                    },
                    headers={
                        "x-call-summary-secret": call_summary_secret or "",
                    },
                )
                if resp.status_code >= 300:
                    logger.warning(
                        f"⚠️ Failed to persist call summary to web app: {resp.status_code} {resp.text}"
                    )
        except Exception as e:
            logger.warning(f"⚠️ Error posting call summary to web app: {e}")

    return {
        "received": True,
        "conversation_id": conversation_id,
        "callSid": call_sid,
        "status": status,
        "neofs_uri": neofs_uri,
    }


# A2A Endpoint

@app.post("/v1/rpc", response_model=A2AResponse)
async def handle_a2a_request(request: Request):
    """
    Main A2A RPC endpoint.
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
        return create_success_response(message.id, {"status": "ok", "agent": "caller"})
    
    elif message.method == A2AMethod.GET_CAPABILITIES.value:
        caps = agent.get_status() if agent else {}
        return create_success_response(message.id, {
            "agent": "archive_caller",
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

@app.post("/call")
async def manual_call(phone_number: str, script: str):
    """Manual call endpoint for testing"""
    if not agent or not agent.llm_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    prompt = f"Call {phone_number} with this script: {script}"
    response = await agent.llm_agent.run(prompt)
    return {"response": response}


@app.post("/sms")
async def manual_sms(phone_number: str, message: str):
    """Manual SMS endpoint for testing"""
    if not agent or not agent.llm_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    prompt = f"Send SMS to {phone_number}: {message}"
    response = await agent.llm_agent.run(prompt)
    return {"response": response}


def run_server():
    """Run the Caller Agent server"""
    port = int(os.getenv("CALLER_PORT", "3003"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_server()

