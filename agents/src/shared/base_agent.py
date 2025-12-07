"""
Base Archive Agent

Abstract base class for all Archive Protocol agents.
Provides:
- Wallet management
- Event subscription
- Bidding workflow
- Job execution framework
"""

import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from pydantic import Field

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.tools.base import BaseTool
from spoon_ai.chat import ChatBot

from .config import JobType, JOB_TYPE_LABELS, get_contract_addresses
from .wallet import AgentWallet, create_wallet_from_env
from .events import EventListener, JobPostedEvent, BidAcceptedEvent
from .contracts import get_contracts, place_bid, get_job
from .elevenlabs import ElevenLabsClient
from .neofs import get_neofs_client
import httpx

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Agent capabilities for job matching"""
    TIKTOK_SCRAPE = "tiktok_scrape"
    WEB_SCRAPE = "web_scrape"
    PHONE_CALL = "phone_call"
    DATA_ANALYSIS = "data_analysis"
    JOB_ORCHESTRATION = "job_orchestration"


@dataclass
class BidDecision:
    """Result of bid evaluation"""
    should_bid: bool
    proposed_amount: int = 0  # in USDC micro-units (6 decimals)
    estimated_time: int = 0   # in seconds
    reasoning: str = ""
    confidence: float = 0.0   # 0.0 to 1.0


@dataclass
class ActiveJob:
    """Tracking for an active job"""
    job_id: int
    bid_id: int
    job_type: int
    description: str
    budget: int
    deadline: int
    status: str = "accepted"  # accepted, in_progress, completed, failed
    metadata_uri: str = ""


class BaseArchiveAgent(ABC):
    """
    Base class for Archive Protocol agents.
    
    Each agent:
    - Has its own wallet
    - Listens for relevant events
    - Evaluates jobs and decides whether to bid
    - Executes accepted jobs
    """
    
    # Agent configuration (override in subclass)
    agent_type: str = "base"
    agent_name: str = "Archive Agent"
    capabilities: list[AgentCapability] = []
    supported_job_types: list[JobType] = []
    
    # Bidding configuration
    min_profit_margin: float = 0.1  # 10%
    max_concurrent_jobs: int = 5
    auto_bid_enabled: bool = True
    
    def __init__(self):
        """Initialize the base agent"""
        self.wallet: Optional[AgentWallet] = None
        self.event_listener: Optional[EventListener] = None
        self.active_jobs: dict[int, ActiveJob] = {}
        self.llm_agent: Optional[ToolCallAgent] = None
        
        self._running = False
        self._contracts = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize agent components"""
        if self._initialized:
            return
        logger.info(f"Initializing {self.agent_name}...")
        
        # Initialize wallet
        self.wallet = create_wallet_from_env(self.agent_type)
        if self.wallet:
            balance = self.wallet.get_balance()
            logger.info(f"  Wallet: {self.wallet.address}")
            logger.info(f"  Balance: {balance.native} GAS, {balance.usdc} USDC")
        else:
            logger.warning(f"  No wallet configured for {self.agent_type}")
        
        # Initialize contracts
        private_key = os.getenv(f"{self.agent_type.upper()}_PRIVATE_KEY")
        if private_key:
            try:
                self._contracts = get_contracts(private_key)
                logger.info("  Connected to blockchain contracts")
            except Exception as e:
                logger.warning(f"  Could not connect to contracts: {e}")
        
        # Initialize event listener
        self.event_listener = EventListener()
        self.event_listener.on_job_posted(self._on_job_posted)
        self.event_listener.on_bid_accepted(self._on_bid_accepted)
        logger.info("  Event listener configured")
        
        # Initialize LLM agent with tools
        self.llm_agent = await self._create_llm_agent()
        logger.info("  LLM agent initialized")
        
        logger.info(f"✅ {self.agent_name} ready")
        self._initialized = True
    
    @abstractmethod
    async def _create_llm_agent(self) -> ToolCallAgent:
        """Create the SpoonOS ToolCallAgent with appropriate tools"""
        pass
    
    @abstractmethod
    def get_bidding_prompt(self, job: JobPostedEvent) -> str:
        """
        Generate prompt for LLM to evaluate whether to bid on a job.
        
        Should return a prompt that asks the LLM to analyze the job
        and return a structured decision.
        """
        pass
    
    @abstractmethod
    async def execute_job(self, job: ActiveJob) -> dict:
        """
        Execute an accepted job.
        
        Returns:
            Result dict with at least 'success' and 'result' keys
        """
        pass
    
    def can_handle_job_type(self, job_type: int) -> bool:
        """Check if this agent can handle a job type"""
        return JobType(job_type) in self.supported_job_types
    
    async def _on_job_posted(self, event: JobPostedEvent):
        """Handle JobPosted event"""
        logger.info(f"📋 New job posted: #{event.job_id} - {JOB_TYPE_LABELS.get(JobType(event.job_type), 'Unknown')}")
        
        # Check if we can handle this job type
        if not self.can_handle_job_type(event.job_type):
            logger.debug(f"  Skipping job #{event.job_id} - not our job type")
            return
        
        # Check concurrent job limit
        if len(self.active_jobs) >= self.max_concurrent_jobs:
            logger.warning(f"  Skipping job #{event.job_id} - at capacity")
            return
        
        # Evaluate and potentially bid
        if self.auto_bid_enabled:
            await self._evaluate_and_bid(event)
    
    async def _evaluate_and_bid(self, job: JobPostedEvent):
        """Evaluate a job and decide whether to bid"""
        logger.info(f"🤔 Evaluating job #{job.job_id}...")
        
        # Generate bidding prompt
        prompt = self.get_bidding_prompt(job)
        
        # Ask LLM to evaluate
        try:
            if self.llm_agent:
                response = await self.llm_agent.run(prompt)
                decision = self._parse_bid_decision(response, job)
            else:
                # Fallback: simple heuristic
                decision = self._heuristic_bid_decision(job)
        except Exception as e:
            logger.error(f"Error evaluating job #{job.job_id}: {e}")
            return
        
        logger.info(f"  Decision: {'BID' if decision.should_bid else 'SKIP'}")
        logger.info(f"  Reasoning: {decision.reasoning}")
        
        if decision.should_bid and self._contracts:
            await self._place_bid(job, decision)
    
    def _parse_bid_decision(self, llm_response: str, job: JobPostedEvent) -> BidDecision:
        """Parse LLM response into a bid decision"""
        # Try to extract structured data from response
        response_lower = llm_response.lower()
        
        should_bid = any(phrase in response_lower for phrase in [
            "should bid", "recommend bidding", "will bid", "place a bid",
            "yes, bid", "accept this job", "take this job"
        ])
        
        # Extract amount if mentioned (look for numbers near 'usdc' or '$')
        import re
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:usdc|\$|dollars?)', response_lower)
        proposed_amount = int(float(amount_match.group(1)) * 1_000_000) if amount_match else job.budget
        
        # Extract time estimate
        time_match = re.search(r'(\d+)\s*(?:hour|hr)', response_lower)
        estimated_time = int(time_match.group(1)) * 3600 if time_match else 3600  # default 1 hour
        
        return BidDecision(
            should_bid=should_bid,
            proposed_amount=proposed_amount,
            estimated_time=estimated_time,
            reasoning=llm_response[:200],
            confidence=0.7 if should_bid else 0.3
        )
    
    def _heuristic_bid_decision(self, job: JobPostedEvent) -> BidDecision:
        """Simple heuristic bid decision when LLM is unavailable"""
        # Check if budget is reasonable
        min_acceptable = 1_000_000  # 1 USDC minimum
        
        if job.budget < min_acceptable:
            return BidDecision(
                should_bid=False,
                reasoning=f"Budget too low: {job.budget / 1_000_000} USDC"
            )
        
        # Calculate our bid (take 80% of budget to be competitive)
        proposed_amount = int(job.budget * 0.8)
        
        return BidDecision(
            should_bid=True,
            proposed_amount=proposed_amount,
            estimated_time=3600,  # 1 hour
            reasoning="Heuristic bid: job type matches capabilities",
            confidence=0.5
        )
    
    async def _place_bid(self, job: JobPostedEvent, decision: BidDecision):
        """Place a bid on the blockchain"""
        if not self._contracts or not self.wallet:
            logger.error("Cannot place bid: contracts or wallet not initialized")
            return
        
        logger.info(f"💰 Placing bid on job #{job.job_id}")
        logger.info(f"   Amount: {decision.proposed_amount / 1_000_000} USDC")
        logger.info(f"   Est. Time: {decision.estimated_time / 3600:.1f} hours")
        
        metadata_uri = f"ipfs://{self.agent_type}-bid-{job.job_id}"
        try:
            bid_id = place_bid(
                self._contracts,
                job.job_id,
                decision.proposed_amount,
                decision.estimated_time,
                metadata_uri
            )
            logger.info(
                "📨 Bid created | job_id=%s bid_id=%s amount=%.2f USDC eta=%.1f h metadata=%s",
                job.job_id,
                bid_id,
                decision.proposed_amount / 1_000_000,
                decision.estimated_time / 3600,
                metadata_uri,
            )
        except Exception as e:
            logger.error(f"❌ Failed to place bid: {e}")
    
    async def _on_bid_accepted(self, event: BidAcceptedEvent):
        """Handle BidAccepted event"""
        # Check if this is our bid (by comparing worker address)
        if not self.wallet or event.worker.lower() != self.wallet.address.lower():
            return
        
        logger.info(f"🎉 Our bid was accepted! Job #{event.job_id}")
        
        # Get full job details
        job_details = None
        if self._contracts:
            try:
                job_details = get_job(self._contracts, event.job_id)
            except Exception as e:
                logger.error(f"Could not fetch job details: {e}")
        
        # Safely unpack job state
        job_state = job_details[0] if job_details and len(job_details) > 0 else None
        bids = job_details[1] if job_details and len(job_details) > 1 else []

        job_type_val = job_state[2] if job_state and len(job_state) > 2 else 0
        job_description = job_state[1] if job_state and len(job_state) > 1 else ""
        job_deadline = job_state[4] if job_state and len(job_state) > 4 else 0

        # Resolve job metadata URI with fallback to JobRegistry when OrderBook value is missing
        job_metadata_uri = self._resolve_job_metadata_uri(job_state, event.job_id)

        # Track the active job
        active_job = ActiveJob(
            job_id=event.job_id,
            bid_id=event.bid_id,
            job_type=job_type_val,
            description=job_description,
            budget=event.amount,
            deadline=job_deadline,
            status="accepted",
            metadata_uri=job_metadata_uri,
        )
        self.active_jobs[event.job_id] = active_job
        
        # Fire-and-forget: send metadata to ElevenLabs
        asyncio.create_task(self._send_to_elevenlabs(event, job_details, job_metadata_uri))

        # Start executing the job
        asyncio.create_task(self._execute_job_task(active_job))
    
    async def _execute_job_task(self, job: ActiveJob):
        """Execute job in background task"""
        logger.info(f"🔄 Starting execution of job #{job.job_id}")
        job.status = "in_progress"
        
        try:
            result = await self.execute_job(job)
            
            if result.get('success'):
                job.status = "completed"
                logger.info(f"✅ Job #{job.job_id} completed successfully")
                # TODO: Submit delivery proof
            else:
                job.status = "failed"
                logger.error(f"❌ Job #{job.job_id} failed: {result.get('error')}")
        except Exception as e:
            job.status = "failed"
            logger.error(f"❌ Job #{job.job_id} exception: {e}")
        finally:
            # Remove from active jobs after some delay
            await asyncio.sleep(60)
            self.active_jobs.pop(job.job_id, None)
    
    async def start(self):
        """Start the agent"""
        if not self._initialized:
            await self.initialize()
        self._running = True

        if self.event_listener:
            await self.event_listener.catch_up()
        
        # Start event listener in background
        asyncio.create_task(self.event_listener.start())
        
        logger.info(f"🚀 {self.agent_name} is running")
    
    def stop(self):
        """Stop the agent"""
        self._running = False
        if self.event_listener:
            self.event_listener.stop()
        logger.info(f"👋 {self.agent_name} stopped")
    
    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_type": self.agent_type,
            "agent_name": self.agent_name,
            "wallet_address": self.wallet.address if self.wallet else None,
            "capabilities": [c.value for c in self.capabilities],
            "supported_job_types": [jt.name for jt in self.supported_job_types],
            "active_jobs": len(self.active_jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "auto_bid_enabled": self.auto_bid_enabled,
            "running": self._running,
        }

    async def _fetch_job_metadata(self, metadata_uri: str) -> dict:
        """
        Fetch job metadata from NeoFS (neofs://cid/oid) or HTTP(S).
        Returns parsed JSON dict or {} on failure.
        """
        if not metadata_uri:
            return {}
        try:
            if metadata_uri.startswith("neofs://"):
                _, rest = metadata_uri.split("neofs://", 1)
                parts = rest.split("/", 1)
                if len(parts) != 2:
                    return {}
                container_id, object_id = parts
                client = get_neofs_client()
                try:
                    data = await client.download_object(object_id, container_id)
                    import json as _json
                    return _json.loads(data.decode("utf-8"))
                finally:
                    await client.close()
            elif metadata_uri.startswith("http://") or metadata_uri.startswith("https://"):
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(metadata_uri)
                    resp.raise_for_status()
                    return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch job metadata from {metadata_uri}: {e}")
        return {}

    def _resolve_job_metadata_uri(self, job_state: Any, job_id: int) -> str:
        """
        Resolve job metadata URI.
        Priority:
          1) JobRegistry.getJob(job_id) -> metadata.metadataURI
          2) Fallback to agent-generated NeoFS metadata if tracked locally
        Note: OrderBook.JobState does NOT contain metadataURI; avoid using it.
        """
        def _decode_uri(val: Any) -> str:
            if isinstance(val, bytes):
                try:
                    return val.decode("utf-8").strip("\x00")
                except Exception:
                    return ""
            return str(val) if val else ""

        # Primary: JobRegistry.getJob(job_id)
        if self._contracts and getattr(self._contracts, "job_registry", None):
            try:
                jr_job = self._contracts.job_registry.functions.getJob(job_id).call()
                stored_job = jr_job[0] if jr_job else None  # (StoredJob)
                metadata = stored_job[0] if stored_job and len(stored_job) > 0 else None  # (JobMetadata)
                uri_from_registry = _decode_uri(metadata[3] if metadata and len(metadata) > 3 else "")
                if uri_from_registry:
                    logger.info("Resolved job metadata URI from JobRegistry.getJob: %s", uri_from_registry)
                    return uri_from_registry
            except Exception as e:
                logger.warning("Failed to resolve metadata URI from JobRegistry for job %s: %s", job_id, e)

        # Fallback: locally tracked active job metadata
        active = self.active_jobs.get(job_id)
        if active and getattr(active, "metadata_uri", None):
            logger.info("Using active job metadata URI fallback: %s", active.metadata_uri)
            return active.metadata_uri

        logger.warning("No job metadata URI found for job %s", job_id)
        return ""

    async def _send_to_elevenlabs(self, event: BidAcceptedEvent, job_details: Any, job_metadata_uri: str = ""):
        """
        Build a JSON payload with job/bid details and send to ElevenLabs outbound call endpoint.
        Pulls metadata from job_metadata_uri (NeoFS/HTTP) to populate dynamic variables.
        """
        client = ElevenLabsClient()
        if not client.is_configured():
            logger.warning("ELEVENLABS not configured; skipping call")
            return
        try:
            job_state = None
            bids = []
            if job_details:
                try:
                    # OrderBook getJob returns (JobState, Bid[])
                    job_state = job_details[0]
                    bids = job_details[1] if len(job_details) > 1 else []
                except Exception:
                    pass

            accepted_bid = None
            for b in bids:
                # Bid tuple: id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt
                try:
                    if int(b[0]) == int(event.bid_id):
                        accepted_bid = b
                        break
                except Exception:
                    continue

            price_usdc = 0.0
            eta_seconds = 0
            bidder = event.worker
            bid_metadata = ""
            if accepted_bid and len(accepted_bid) >= 7:
                try:
                    price_usdc = int(accepted_bid[3]) / 1_000_000  # USDC 6 decimals
                    eta_seconds = int(accepted_bid[4])
                    bidder = accepted_bid[2]
                    bid_metadata = accepted_bid[6] or ""
                except Exception:
                    pass

            poster = ""
            job_description = ""
            if job_state:
                if len(job_state) >= 1:
                    poster = job_state[0]
                if len(job_state) >= 2:
                    job_description = job_state[1]

            # Fetch metadata from URI and log for visibility
            metadata_doc = await self._fetch_job_metadata(job_metadata_uri)
            logger.info(
                "📄 Parsed job metadata | job_id=%s uri=%s data=%s",
                event.job_id,
                job_metadata_uri,
                metadata_doc,
            )

            # Build dynamic variables for the outbound call
            tags_value = metadata_doc.get("tags", [])
            if isinstance(tags_value, list):
                tags_value = ", ".join([str(t) for t in tags_value])
            elif not isinstance(tags_value, str):
                tags_value = str(tags_value) if tags_value is not None else ""

            # Pass through the raw job payload (no LLM parsing needed)
            raw_job_payload = metadata_doc.get("job", "")

            dynamic_vars = {
                "jobId": event.job_id,
                "acceptedBidId": event.bid_id,
                "poster": poster,
                "bidder": bidder,
                "priceUsdc": price_usdc,
                "etaSeconds": eta_seconds,
                "jobDescription": job_description,
                "jobTags": tags_value,
                "jobMetadataUri": job_metadata_uri,
                "bidMetadataUri": bid_metadata,
                "txHash": event.tx_hash,
                "job": raw_job_payload,
                "time": metadata_doc.get("time", "8pm"),
                "num_of_people": metadata_doc.get("party_size", metadata_doc.get("num_of_people", 4)),
                "date": metadata_doc.get("date", "7th December"),
                "user_name": metadata_doc.get("user_name", "katya"),
                "user": metadata_doc.get("user", bidder),
                "phone_to_call": metadata_doc.get("phone_to_call", client.phone_number),
                "notes": metadata_doc.get("notes", ""),
            }

            payload = {
                "agent_id": client.agent_id,
                "agent_phone_number_id": client.phone_number_id,
                "to_number": metadata_doc.get("phone_to_call", ""),
                "authenticated": True,
                "conversation_initiation_client_data": {
                    "type": "conversation_initiation_client_data",
                    "dynamic_variables": dynamic_vars,
                },
            }

            # Fallback destination if metadata is missing
            if not payload["to_number"]:
                env_to = os.getenv("ELEVENLABS_TO_NUMBER") or client.phone_number
                payload["to_number"] = env_to

            logger.info(f"📞 Sending job #{event.job_id} bid #{event.bid_id} to ElevenLabs outbound call...")
            resp = await client.send_call(payload)
            logger.info(f"✅ ElevenLabs outbound response: {resp}")
        except Exception as e:
            logger.error(f"❌ Failed to send to ElevenLabs: {e}")
