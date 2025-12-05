"""
Manager Agent - Job Orchestrator

The Manager Agent is different from worker agents:
- It orchestrates jobs by posting them and coordinating workers
- Listens for JobPosted events to track jobs it posted
- Reviews bids from workers and selects the best ones
- Monitors delivery submissions and approves them
- Releases payments when work is complete

The Manager does NOT bid on jobs - it creates them.
"""

import asyncio
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass, field
from pydantic import Field

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

from ..shared.config import JobType, JOB_TYPE_LABELS
from ..shared.wallet import AgentWallet, create_wallet_from_env
from ..shared.events import EventListener, JobPostedEvent, BidPlacedEvent, DeliverySubmittedEvent
from ..shared.wallet_tools import get_wallet_tools
from ..shared.booking import analyze_slots
from ..shared.bevec import BeVecClient, VectorRecord, create_bevec_client
from ..shared.embedding import embed_text
from ..shared.contracts import get_contracts, post_job

from .tools import get_manager_tools

logger = logging.getLogger(__name__)


# ==============================================================================
# SYSTEM PROMPTS
# ==============================================================================

ORCHESTRATION_SYSTEM_PROMPT = """
You are the Manager Agent for Archive Protocol, a decentralized multi-agent system on NeoX blockchain.

Your role is to ORCHESTRATE job execution - you create jobs and coordinate worker agents to complete them.

## Core Responsibilities

1. **Job Decomposition**: When you receive a complex request, break it down into sub-tasks:
   - TIKTOK_SCRAPE: For TikTok/social media data collection
   - WEB_SCRAPE: For web search and data extraction
   - CALL_VERIFICATION: For phone-based verification or booking
   - DATA_ANALYSIS: For processing and analyzing data

2. **Bid Management**: After posting jobs, worker agents will submit bids. You must:
   - Wait for bids to come in (check after 30-60 seconds)
   - Analyze all bids for cost, speed, and quality
   - Select the best worker for each sub-task
   - Accept the winning bid to lock funds in escrow

3. **Worker Coordination**: Once bids are accepted:
   - Send A2A messages to workers with task details
   - Monitor progress via status updates
   - Handle any issues or re-assignments

4. **Delivery Approval**: When workers submit deliveries:
   - Review the delivered work
   - Verify it meets requirements
   - Approve delivery to release payment
   - Handle disputes if work is unsatisfactory

## Decision Guidelines

When selecting bids, consider:
- **Cost**: Lower bids save budget for the job poster
- **Speed**: Faster estimated times mean quicker results
- **Reputation**: Workers with higher reputation are more reliable
- Use "balanced" priority by default, "cost" for budget-conscious jobs, "speed" for urgent jobs

## Available Worker Agents

- **Scraper Agent**: Handles TikTok scraping and web data collection
- **Caller Agent**: Handles phone calls and voice verification

Always explain your reasoning before taking actions. Be efficient with funds and time.
"""

NEXT_STEP_PROMPT = """
Analyze the current state and decide the next action:

1. If a new job needs processing → decompose it into sub-tasks
2. If sub-tasks are defined → check for worker bids
3. If bids are available → analyze and select the best worker
4. If a bid is selected → accept it to assign the work
5. If work is assigned → send execution request to worker
6. If delivery is submitted → review and approve/reject
7. If all tasks complete → finalize the job

Provide clear reasoning for each decision.
"""


# ==============================================================================
# TRACKED JOBS
# ==============================================================================

@dataclass
class TrackedJob:
    """A job being managed by this agent"""
    job_id: int
    description: str
    job_type: int
    budget: int
    status: str = "posted"  # posted, bidding, assigned, in_progress, delivered, completed, failed
    sub_tasks: list = field(default_factory=list)
    accepted_bids: dict = field(default_factory=dict)  # task_index -> bid_id
    deliveries: list = field(default_factory=list)


# ==============================================================================
# MANAGER AGENT
# ==============================================================================

class ManagerAgent:
    """
    Manager Agent for Archive Protocol.
    
    Unlike worker agents that bid on jobs, the Manager:
    - Posts jobs (or receives them from users)
    - Coordinates worker agents
    - Manages the full job lifecycle
    """
    
    agent_type: str = "manager"
    agent_name: str = "Archive Manager"
    
    def __init__(self):
        """Initialize the Manager Agent"""
        self.wallet: Optional[AgentWallet] = None
        self.event_listener: Optional[EventListener] = None
        self.llm_agent: Optional[ToolCallAgent] = None
        self.vector_client: Optional[BeVecClient] = None
        self._contracts = None
        
        # Track jobs we're managing
        self.tracked_jobs: dict[int, TrackedJob] = {}
        
        self._running = False
    
    async def initialize(self):
        """Initialize agent components"""
        logger.info(f"Initializing {self.agent_name}...")
        
        # Initialize wallet
        self.wallet = create_wallet_from_env(self.agent_type)
        if self.wallet:
            balance = self.wallet.get_balance()
            logger.info(f"  Wallet: {self.wallet.address}")
            logger.info(f"  Balance: {balance.native} GAS, {balance.usdc} USDC")
        else:
            logger.warning(f"  No wallet configured for {self.agent_type}")
        
        # Initialize event listener
        self.event_listener = EventListener()
        self.event_listener.on_job_posted(self._on_job_posted)
        self.event_listener.on_bid_submitted(self._on_bid_submitted)
        self.event_listener.on_delivery_submitted(self._on_delivery_submitted)
        logger.info("  Event listener configured")

        # Initialize vector client (beVec)
        self.vector_client = create_bevec_client()
        if self.vector_client:
            logger.info("  beVec client configured")
        else:
            logger.info("  beVec not configured (set BEVEC_ENDPOINT to enable)")

        # Initialize contracts for job posting
        if self.wallet:
            try:
                self._contracts = get_contracts(self.wallet.private_key)
                logger.info("  Connected to blockchain contracts")
            except Exception as e:
                logger.warning(f"  Could not connect to contracts: {e}")

        # Initialize LLM agent with tools
        self.llm_agent = await self._create_llm_agent()
        logger.info("  LLM agent initialized")
        
        logger.info(f"✅ {self.agent_name} ready")
    
    async def _create_llm_agent(self) -> ToolCallAgent:
        """Create the SpoonOS ToolCallAgent with manager tools"""
        if not self.wallet:
            raise RuntimeError("Wallet must be initialized before creating LLM agent")
        
        # Combine manager tools with wallet tools
        tools = get_manager_tools(self.wallet, vector_client=self.vector_client) + get_wallet_tools(self.wallet)
        
        agent = ToolCallAgent(
            name=self.agent_name,
            description="Archive Protocol job orchestrator",
            system_prompt=ORCHESTRATION_SYSTEM_PROMPT,
            next_step_prompt=NEXT_STEP_PROMPT,
            max_steps=15,
            available_tools=ToolManager(tools),
            llm=ChatBot(
                llm_provider="anthropic",
                model_name="claude-sonnet-4-20250514"
            )
        )
        
        return agent
    
    async def start(self):
        """Start the Manager Agent"""
        self._running = True
        
        if self.event_listener:
            asyncio.create_task(self.event_listener.start())
            logger.info("Event listener started")
    
    async def stop(self):
        """Stop the Manager Agent"""
        self._running = False
        
        if self.event_listener:
            await self.event_listener.stop()
            logger.info("Event listener stopped")

        if self.vector_client:
            try:
                await self.vector_client.close()
            except Exception:
                pass
    
    # ==========================================================================
    # EVENT HANDLERS
    # ==========================================================================
    
    async def _on_job_posted(self, event: JobPostedEvent):
        """Handle JobPosted events - track jobs we care about"""
        logger.info(f"📋 Job posted: ID={event.job_id}, Type={JOB_TYPE_LABELS.get(event.job_type, 'UNKNOWN')}")
        
        # Check if this job was posted by us (or if we should manage it)
        # event.client is the job poster address
        if self.wallet and event.client.lower() == self.wallet.address.lower():
            logger.info(f"   This is our job - tracking it")
            self.tracked_jobs[event.job_id] = TrackedJob(
                job_id=event.job_id,
                description=event.description,
                job_type=event.job_type,
                budget=event.budget,
                status="posted"
            )
            
            # Trigger job decomposition
            asyncio.create_task(self._process_new_job(event))
    
    async def _on_bid_submitted(self, event: BidPlacedEvent):
        """Handle BidSubmitted events for jobs we're managing"""
        if event.job_id in self.tracked_jobs:
            job = self.tracked_jobs[event.job_id]
            logger.info(f"📨 New bid for job {event.job_id}: {event.amount} from {event.bidder}")
            
            # Update status
            if job.status == "posted":
                job.status = "bidding"
            
            # Trigger bid evaluation
            asyncio.create_task(self._evaluate_bid(event))
    
    async def _on_delivery_submitted(self, event: DeliverySubmittedEvent):
        """Handle DeliverySubmitted events for jobs we're managing"""
        if event.job_id in self.tracked_jobs:
            job = self.tracked_jobs[event.job_id]
            logger.info(f"📦 Delivery submitted for job {event.job_id}")
            
            job.status = "delivered"
            job.deliveries.append({
                "worker": event.worker,
                "result_uri": event.result_uri,
                "timestamp": event.timestamp
            })
            
            # Trigger delivery review
            asyncio.create_task(self._review_delivery(event))
    
    # ==========================================================================
    # JOB PROCESSING
    # ==========================================================================
    
    async def _process_new_job(self, event: JobPostedEvent):
        """Process a newly posted job"""
        if not self.llm_agent:
            logger.error("LLM agent not initialized")
            return
        
        logger.info(f"🔄 Processing job {event.job_id}...")
        
        prompt = f"""
        A new job has been posted that we need to manage:
        
        Job ID: {event.job_id}
        Job Type: {JOB_TYPE_LABELS.get(event.job_type, 'UNKNOWN')}
        Budget: {event.budget / 1_000_000:.2f} USDC
        Description: {event.description}
        
        Please:
        1. Use decompose_job to break this into sub-tasks
        2. We'll wait for worker bids to come in
        """
        
        try:
            response = await self.llm_agent.run(prompt)
            logger.info(f"✅ Job {event.job_id} decomposed: {response[:200]}...")
        except Exception as e:
            logger.error(f"❌ Error processing job {event.job_id}: {e}")
    
    async def _evaluate_bid(self, event: BidPlacedEvent):
        """Evaluate incoming bids and decide whether to accept"""
        if not self.llm_agent:
            return
        
        # Wait a bit for more bids to come in
        await asyncio.sleep(30)
        
        job = self.tracked_jobs.get(event.job_id)
        if not job or job.status == "assigned":
            return  # Already handled
        
        prompt = f"""
        Bids have come in for job {event.job_id}.
        
        Please:
        1. Use get_bids_for_job to see all bids
        2. Use select_best_bid to analyze them
        3. Use accept_bid to accept the winning bid
        """
        
        try:
            response = await self.llm_agent.run(prompt)
            job.status = "assigned"
            logger.info(f"✅ Bid accepted for job {event.job_id}")
        except Exception as e:
            logger.error(f"❌ Error evaluating bids for job {event.job_id}: {e}")
    
    async def _review_delivery(self, event: DeliverySubmittedEvent):
        """Review a delivery and decide whether to approve"""
        if not self.llm_agent:
            return
        
        job = self.tracked_jobs.get(event.job_id)
        if not job:
            return
        
        prompt = f"""
        A worker has submitted a delivery for job {event.job_id}.
        
        Delivery details:
        - Worker: {event.worker}
        - Result URI: {event.result_uri}
        
        Please:
        1. Review the delivery (the result URI contains the work)
        2. If satisfactory, use approve_delivery to release payment
        3. If not, we can dispute (not implemented yet)
        """
        
        try:
            response = await self.llm_agent.run(prompt)
            job.status = "completed"
            logger.info(f"✅ Job {event.job_id} completed")
        except Exception as e:
            logger.error(f"❌ Error reviewing delivery for job {event.job_id}: {e}")
    
    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    async def plan_booking(
        self,
        user_prompt: str,
        provided_slots: dict | None = None,
        top_k_experiences: int = 4,
        top_k_playbooks: int = 2,
    ) -> dict:
        """Slot-fill a booking request and gather RAG context."""
        slot_analysis = analyze_slots(user_prompt, provided_slots)
        retrieval = await self._retrieve_booking_context(
            user_prompt=user_prompt,
            tags=slot_analysis.tags,
            top_k_experiences=top_k_experiences,
            top_k_playbooks=top_k_playbooks,
        )

        return {
            "slots": slot_analysis.slots,
            "missing_slots": slot_analysis.missing_slots,
            "questions": slot_analysis.questions,
            "tags": slot_analysis.tags,
            "retrieval": retrieval,
        }

    async def _retrieve_booking_context(
        self,
        user_prompt: str,
        tags: list[str],
        top_k_experiences: int = 4,
        top_k_playbooks: int = 2,
    ) -> dict:
        """Query beVec for prior experiences and playbooks to ground planning."""
        if not self.vector_client:
            return {
                "enabled": False,
                "reason": "BEVEC_ENDPOINT not configured",
                "experiences": [],
                "playbooks": [],
            }

        query_text = f"Restaurant booking intent: {user_prompt}\nTags: {', '.join(tags)}"
        try:
            vector = await embed_text(query_text)
        except Exception as e:
            return {
                "enabled": False,
                "reason": f"Embedding failed: {e}",
                "experiences": [],
                "playbooks": [],
            }

        experiences = []
        playbooks = []

        try:
            experiences = [r.__dict__ for r in await self.vector_client.query(
                collection="user_experiences",
                vector=vector,
                top_k=top_k_experiences,
                tags=tags,
            )]
        except Exception as e:
            logger.warning(f"beVec experiences query failed: {e}")

        try:
            playbooks = [r.__dict__ for r in await self.vector_client.query(
                collection="booking_playbooks",
                vector=vector,
                top_k=top_k_playbooks,
                tags=["booking"],
            )]
        except Exception as e:
            logger.warning(f"beVec playbooks query failed: {e}")

        return {
            "enabled": True,
            "experiences": experiences,
            "playbooks": playbooks,
        }

    async def persist_booking_experience(
        self,
        summary: str,
        metadata: dict,
        raw_payload: dict | None = None,
    ) -> dict:
        """Persist a completed booking experience to NeoFS and beVec."""
        if not self.vector_client:
            return {"success": False, "error": "beVec not configured"}

        neofs_uri = None
        if raw_payload:
            try:
                from ..shared.neofs import get_neofs_client

                client = get_neofs_client()
                result = await client.upload_json(raw_payload, filename="booking-result.json")
                neofs_uri = f"neofs://{result.container_id}/{result.object_id}"
            except Exception as e:
                logger.warning(f"NeoFS upload failed: {e}")

        try:
            vector = await embed_text(summary)
        except Exception as e:
            return {"success": False, "error": f"Embedding failed: {e}"}

        record_id_source = metadata.get("job_id") or metadata.get("user_id") or summary
        record_id = hashlib.sha256(str(record_id_source).encode("utf-8")).hexdigest()

        enriched_metadata = {**metadata}
        if neofs_uri:
            enriched_metadata["source_uri"] = neofs_uri

        try:
            await self.vector_client.upsert(
                collection="user_experiences",
                records=[VectorRecord(id=record_id, vector=vector, metadata=enriched_metadata)],
            )
        except Exception as e:
            return {"success": False, "error": f"beVec upsert failed: {e}"}

        return {
            "success": True,
            "record_id": record_id,
            "source_uri": neofs_uri,
        }

    async def post_booking_job(
        self,
        description: str,
        job_type: int = JobType.COMPOSITE.value,
        budget: int = 0,
        deadline: int = 0,
    ) -> dict:
        """Post a booking job to the order book."""
        if not self._contracts:
            return {"success": False, "error": "Contracts not initialized"}

        try:
            job_id = post_job(self._contracts, description, job_type, budget, deadline)
            return {"success": True, "job_id": job_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def process_request(self, request: str) -> str:
        """
        Process a user request.
        
        This could be:
        - A new job to post and coordinate
        - A query about existing jobs
        - Instructions to manage workers
        """
        if not self.llm_agent:
            return "Agent not initialized"
        
        return await self.llm_agent.run(request)
    
    def get_tracked_jobs(self) -> dict:
        """Get summary of all tracked jobs"""
        return {
            job_id: {
                "description": job.description[:100],
                "status": job.status,
                "job_type": JOB_TYPE_LABELS.get(job.job_type, "UNKNOWN"),
                "budget": job.budget / 1_000_000
            }
            for job_id, job in self.tracked_jobs.items()
        }


# ==============================================================================
# FACTORY
# ==============================================================================

async def create_manager_agent() -> ManagerAgent:
    """
    Factory function to create and initialize a Manager Agent.
    
    Returns:
        Configured and initialized ManagerAgent instance
    """
    agent = ManagerAgent()
    await agent.initialize()
    return agent


# ==============================================================================
# MAIN
# ==============================================================================

async def main():
    """Demo: Run the Manager Agent interactively"""
    print("🚀 Archive Manager Agent - SpoonOS Demo")
    print("=" * 60)
    
    agent = await create_manager_agent()
    await agent.start()
    
    # Example job
    demo_request = """
    I need to find a trendy restaurant in Moscow via TikTok and book a table 
    for 2 people this Saturday at 7pm. Verify the reservation by calling them.
    """
    
    print(f"\n📋 Processing request:\n{demo_request.strip()}\n")
    print("-" * 60)
    
    response = await agent.process_request(f"Process this job request: {demo_request}")
    print(f"\n✅ Agent Response:\n{response}")
    
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
