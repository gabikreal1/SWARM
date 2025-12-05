"""
Scraper Agent - Archive Protocol

The Scraper Agent:
1. Listens for scraping job events (TikTok, web)
2. Evaluates jobs and decides whether to bid
3. Executes accepted jobs using Bright Data and web scraping
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

from .tools import create_scraper_tools

logger = logging.getLogger(__name__)


class ScraperLLMAgent(ToolCallAgent):
    """
    SpoonOS ToolCallAgent for the Scraper.
    
    This handles the LLM-driven tool calling.
    """
    
    name: str = "scraper_llm"
    description: str = "LLM agent for executing scraping tasks"
    
    system_prompt: str = """
    You are the Scraper Agent for Archive Protocol, specializing in data extraction.
    
    Your capabilities:
    1. **TikTok Scraping**: Use scrape_tiktok to find:
       - Videos matching search queries
       - Creator information and engagement metrics
       - Trending content in specific niches
    
    2. **Web Scraping**: Use web_scrape for:
       - Business information
       - Contact details and reviews
    
    3. **Delivery**: After scraping:
       - Upload results to NeoFS using upload_to_neofs
       - Compute proof hash using compute_proof_hash
       - Submit delivery using submit_delivery
    
    4. **Wallet**: Check balance and manage funds using wallet tools.
    
    5. **Bidding**: Get job details and place bids using bidding tools.
    
    Always complete tasks thoroughly and upload results to NeoFS for proof.
    """
    
    next_step_prompt: str = """
    Based on the current progress, decide the next action:
    - To scrape TikTok: use scrape_tiktok
    - To scrape web: use web_scrape
    - After scraping: upload_to_neofs, then submit_delivery
    - To check wallet: use get_wallet_balance
    - To bid on job: use place_bid
    """
    
    max_steps: int = 15


class ScraperAgent(BaseArchiveAgent):
    """
    Scraper Agent for Archive Protocol.
    
    Extends BaseArchiveAgent with scraping-specific logic.
    """
    
    agent_type = "scraper"
    agent_name = "Archive Scraper Agent"
    capabilities = [
        AgentCapability.TIKTOK_SCRAPE,
        AgentCapability.WEB_SCRAPE,
    ]
    supported_job_types = [
        JobType.TIKTOK_SCRAPE,
        JobType.WEB_SCRAPE,
    ]
    
    # Bidding configuration
    min_profit_margin = 0.15  # 15% margin
    max_concurrent_jobs = 3
    auto_bid_enabled = True
    
    async def _create_llm_agent(self) -> ToolCallAgent:
        """Create the SpoonOS ToolCallAgent with all tools"""
        # Collect all tools
        all_tools = []
        
        # Scraper-specific tools
        all_tools.extend(create_scraper_tools())
        
        # Wallet tools (with wallet injected)
        wallet_tools = create_wallet_tools(self.wallet)
        all_tools.extend(wallet_tools)
        
        # Bidding tools (with contracts injected)
        bidding_tools = create_bidding_tools(self._contracts, self.agent_type)
        all_tools.extend(bidding_tools)
        
        # Create the agent
        llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        
        agent = ScraperLLMAgent(
            llm=ChatBot(
                llm_provider=llm_provider,
                model_name=model_name
            ),
            available_tools=ToolManager(all_tools)
        )
        
        return agent
    
    def get_bidding_prompt(self, job: JobPostedEvent) -> str:
        """Generate prompt for LLM to evaluate whether to bid on a scraping job"""
        job_type_label = JOB_TYPE_LABELS.get(JobType(job.job_type), "Unknown")
        budget_usdc = job.budget / 1_000_000
        
        return f"""
        Evaluate this scraping job and decide whether to bid:
        
        JOB DETAILS:
        - Job ID: {job.job_id}
        - Type: {job_type_label}
        - Budget: {budget_usdc} USDC
        - Deadline: {job.deadline}
        - Description: {job.description}
        
        YOUR CAPABILITIES:
        - TikTok scraping via Bright Data API
        - General web scraping
        - Current capacity: {self.max_concurrent_jobs - len(self.active_jobs)} jobs available
        
        CONSIDERATIONS:
        1. Can you complete this job type?
        2. Is the budget reasonable for the effort required?
        3. Can you meet the deadline?
        4. Is the description clear enough to execute?
        
        DECISION FORMAT:
        - If you should bid, say "SHOULD BID" and propose:
          - Your bid amount in USDC (should be competitive, typically 70-90% of budget)
          - Estimated completion time in hours
        - If you should skip, say "SHOULD SKIP" and explain why.
        
        Provide your reasoning.
        """
    
    async def execute_job(self, job: ActiveJob) -> dict:
        """Execute an accepted scraping job"""
        logger.info(f"🕷️ Executing scraping job #{job.job_id}")
        
        if not self.llm_agent:
            return {"success": False, "error": "LLM agent not initialized"}
        
        # Determine job type and create execution prompt
        job_type = JobType(job.job_type)
        job_type_label = JOB_TYPE_LABELS.get(job_type, "Unknown")
        
        prompt = f"""
        Execute this {job_type_label} job:
        
        Job ID: {job.job_id}
        Description: {job.description}
        Budget: {job.budget / 1_000_000} USDC
        
        Steps:
        1. Perform the scraping task based on the description
        2. Upload results to NeoFS
        3. Compute the proof hash
        4. Submit delivery to the blockchain
        
        Report each step as you complete it.
        """
        
        try:
            response = await self.llm_agent.run(prompt)
            
            # Check if delivery was submitted (look for success indicators)
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


async def create_scraper_agent() -> ScraperAgent:
    """Factory function to create and initialize a Scraper Agent"""
    agent = ScraperAgent()
    await agent.initialize()
    return agent


async def main():
    """Run the Scraper Agent"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("🕷️ Archive Scraper Agent")
    print("=" * 60)
    
    agent = await create_scraper_agent()
    print(f"\n📊 Status: {agent.get_status()}")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("\n👋 Scraper Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())

    asyncio.run(main())
