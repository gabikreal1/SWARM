"""
Caller Agent - Archive Protocol

The Caller Agent:
1. Listens for phone verification job events
2. Evaluates jobs and decides whether to bid
3. Executes accepted jobs using Twilio
4. Uploads results to NeoFS and submits delivery proofs
"""

import os
import asyncio
import logging
from typing import Optional

from pydantic import Field

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

from ..shared.base_agent import BaseArchiveAgent, AgentCapability, ActiveJob
from ..shared.config import JobType, JOB_TYPE_LABELS
from ..shared.events import JobPostedEvent
from ..shared.wallet_tools import create_wallet_tools
from ..shared.bidding_tools import create_bidding_tools

from .tools import create_caller_tools

logger = logging.getLogger(__name__)


class CallerLLMAgent(ToolCallAgent):
    """
    SpoonOS ToolCallAgent for the Caller.
    
    This handles the LLM-driven tool calling.
    """
    
    name: str = "caller_llm"
    description: str = "LLM agent for executing phone verification tasks"
    
    system_prompt: str = """
    You are the Caller Agent for Archive Protocol, specializing in phone verification.
    
    Your capabilities:
    1. **Phone Calls**: Use make_phone_call to:
       - Verify business information
       - Make reservations
       - Confirm details
    
    2. **SMS**: Use send_sms for follow-up confirmations.
    
    3. **Call Status**: Use get_call_status to check call outcomes.
    
    4. **Delivery**: After calls:
       - Upload results to NeoFS using upload_call_result
       - Compute proof hash using compute_proof_hash
       - Submit delivery using submit_delivery
    
    5. **Wallet & Bidding**: Check balance and manage bids.
    
    IMPORTANT: Always be professional and polite on calls.
    Generate appropriate scripts before making calls.
    """
    
    next_step_prompt: str = """
    Based on the current progress, decide the next action:
    - To make a call: generate script, then use make_phone_call
    - After call: get_call_status, then upload_call_result
    - Finally: submit_delivery with proof hash
    - To check wallet: use get_wallet_balance
    - To bid on job: use place_bid
    """
    
    max_steps: int = 15


class CallerAgent(BaseArchiveAgent):
    """
    Caller Agent for Archive Protocol.
    
    Extends BaseArchiveAgent with phone verification-specific logic.
    """
    
    agent_type = "caller"
    agent_name = "Archive Caller Agent"
    capabilities = [
        AgentCapability.PHONE_CALL,
    ]
    supported_job_types = [
        JobType.CALL_VERIFICATION,
    ]
    
    # Bidding configuration
    min_profit_margin = 0.20  # 20% margin (calls are more expensive)
    max_concurrent_jobs = 2   # Fewer concurrent calls
    auto_bid_enabled = True
    
    async def _create_llm_agent(self) -> ToolCallAgent:
        """Create the SpoonOS ToolCallAgent with all tools"""
        # Collect all tools
        all_tools = []
        
        # Caller-specific tools
        all_tools.extend(create_caller_tools())
        
        # Wallet tools (with wallet injected)
        wallet_tools = create_wallet_tools(self.wallet)
        all_tools.extend(wallet_tools)
        
        # Bidding tools (with contracts injected)
        bidding_tools = create_bidding_tools(self._contracts, self.agent_type)
        all_tools.extend(bidding_tools)
        
        # Create the agent
        llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        
        agent = CallerLLMAgent(
            llm=ChatBot(
                llm_provider=llm_provider,
                model_name=model_name
            ),
            available_tools=ToolManager(all_tools)
        )
        
        return agent
    
    def get_bidding_prompt(self, job: JobPostedEvent) -> str:
        """Generate prompt for LLM to evaluate whether to bid on a calling job"""
        job_type_label = JOB_TYPE_LABELS.get(JobType(job.job_type), "Unknown")
        budget_usdc = job.budget / 1_000_000
        
        return f"""
        Evaluate this phone verification job and decide whether to bid:
        
        JOB DETAILS:
        - Job ID: {job.job_id}
        - Type: {job_type_label}
        - Budget: {budget_usdc} USDC
        - Deadline: {job.deadline}
        - Description: {job.description}
        
        YOUR CAPABILITIES:
        - Twilio phone calls (voice verification)
        - SMS messaging
        - Current capacity: {self.max_concurrent_jobs - len(self.active_jobs)} jobs available
        
        CONSIDERATIONS:
        1. Does this require phone verification you can perform?
        2. Is the budget reasonable for call costs + effort?
        3. Can you complete within the deadline?
        4. Is there a clear phone number or way to find it?
        
        COSTS TO CONSIDER:
        - Twilio call: ~$0.01/min domestic, ~$0.10/min international
        - SMS: ~$0.01 per message
        - Your time: factor in script generation and follow-up
        
        DECISION FORMAT:
        - If you should bid, say "SHOULD BID" and propose:
          - Your bid amount in USDC (account for Twilio costs)
          - Estimated completion time in hours
        - If you should skip, say "SHOULD SKIP" and explain why.
        
        Provide your reasoning.
        """
    
    async def execute_job(self, job: ActiveJob) -> dict:
        """Execute an accepted phone verification job"""
        logger.info(f"📞 Executing phone verification job #{job.job_id}")
        
        if not self.llm_agent:
            return {"success": False, "error": "LLM agent not initialized"}
        
        prompt = f"""
        Execute this phone verification job:
        
        Job ID: {job.job_id}
        Description: {job.description}
        Budget: {job.budget / 1_000_000} USDC
        
        Steps:
        1. Analyze the description to determine:
           - What needs to be verified
           - The phone number to call (or how to find it)
           - Key questions to ask
        
        2. Generate a professional, polite call script
        
        3. Make the call using make_phone_call
        
        4. Check call status with get_call_status
        
        5. Upload results to NeoFS using upload_call_result
        
        6. Submit delivery to blockchain using submit_delivery
        
        Report each step as you complete it.
        """
        
        try:
            response = await self.llm_agent.run(prompt)
            
            # Check if delivery was submitted
            success = any(phrase in response.lower() for phrase in [
                "delivery submitted",
                "submit_delivery",
                "proof submitted",
                "completed successfully"
            ])
            
            return {
                "success": success,
                "result": response,
                "job_id": job.job_id
            }
        except Exception as e:
            logger.error(f"Job execution error: {e}")
            return {"success": False, "error": str(e)}


async def create_caller_agent() -> CallerAgent:
    """Factory function to create and initialize a Caller Agent"""
    agent = CallerAgent()
    await agent.initialize()
    return agent


async def main():
    """Run the Caller Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("📞 Archive Caller Agent")
    print("=" * 60)
    
    agent = await create_caller_agent()
    print(f"\n📊 Status: {agent.get_status()}")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("\n👋 Caller Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())

