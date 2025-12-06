"""
TikTok Hashtag Agent for SpoonOS

Competes on TikTok scraping jobs with a low-bid strategy and filters videos
by requested hashtags.
"""

import os
import asyncio
import logging
from typing import Optional

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

from agents.src.shared.base_agent import BaseArchiveAgent, AgentCapability, ActiveJob
from agents.src.shared.config import JobType, JOB_TYPE_LABELS
from agents.src.shared.events import JobPostedEvent
from agents.src.shared.wallet_tools import create_wallet_tools
from agents.src.shared.bidding_tools import create_bidding_tools
from agents.src.tiktok.tool import create_tiktok_tools
from agents.src.shared.contracts import get_bids_for_job

logger = logging.getLogger(__name__)


class TikTokLLMAgent(ToolCallAgent):
    """LLM-driven executor for TikTok scraping tasks."""

    name: str = "tiktok_llm"
    description: str = "TikTok profile/video scraping and hashtag filtering agent"

    system_prompt: str = """
    You are a TikTok scraping specialist.
    - Use tiktok_search/tiktok_scrape to fetch videos for a profile or search.
    - Filter to the requested hashtags.
    - Keep gas/USDC spend minimal; prefer fast, single-pass scrapes.
    - If a job provides profile and hashtags, scrape that profile and return only matching videos.
    """

    next_step_prompt: str = """
    Decide the next action:
    - If hashtags or profile are provided, call the TikTok tool with profile_url and hashtags.
    - Otherwise, use search to find matching videos.
    - Return concise structured results.
    """

    max_steps: int = 10


class TikTokAgent(BaseArchiveAgent):
    """Low-bid TikTok scraper competing on TIKTOK_SCRAPE jobs."""

    agent_type = "tiktok"
    agent_name = "TikTok Hashtag Agent"
    capabilities = [AgentCapability.TIKTOK_SCRAPE]
    supported_job_types = [JobType.TIKTOK_SCRAPE]

    # Bid aggressively
    min_profit_margin = 0.02  # 2%
    max_concurrent_jobs = 5
    auto_bid_enabled = True
    use_simple_bid = os.getenv("TIKTOK_SIMPLE_BID", "1") == "1"

    def _matches_job(self, job: JobPostedEvent) -> bool:
        """Check if the job description looks like a TikTok scrape we can do."""
        desc = (job.description or "").lower()
        return "tiktok" in desc or "tt" in desc or "hashtag" in desc or "profile" in desc

    def _adjust_bid_for_competition(self, decision, job: JobPostedEvent):
        """Undercut existing bids to stay competitive."""
        try:
            if not self._contracts:
                return decision
            bids = get_bids_for_job(self._contracts, job.job_id)
            if not bids:
                return decision
            current_low = min(b[2] for b in bids)  # assuming tuple (..., amount, ...)
            target = int(max(current_low * 0.95, current_low - 10_000))  # undercut ~5% with floor
            if target > 0 and target < decision.proposed_amount:
                decision.proposed_amount = target
        except Exception as e:
            logger.debug(f"Could not adjust bid for competition: {e}")
        return decision

    async def _create_llm_agent(self) -> ToolCallAgent:
        all_tools = []
        all_tools.extend(create_tiktok_tools())
        all_tools.extend(create_wallet_tools(self.wallet))
        all_tools.extend(create_bidding_tools(self._contracts, self.agent_type))

        llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        model_name = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

        return TikTokLLMAgent(
            llm=ChatBot(llm_provider=llm_provider, model_name=model_name),
            available_tools=ToolManager(all_tools),
        )

    def get_bidding_prompt(self, job: JobPostedEvent) -> str:
        job_type_label = JOB_TYPE_LABELS.get(JobType(job.job_type), "Unknown")
        budget_usdc = job.budget / 1_000_000
        return f"""
        Evaluate this TikTok scraping job and bid low:
        - Job ID: {job.job_id}
        - Type: {job_type_label}
        - Budget: {budget_usdc} USDC
        - Deadline: {job.deadline}
        - Description: {job.description}

        Strategy:
        - Aim for aggressive pricing (60-75% of budget) while staying profitable.
        - Confirm hashtags/profile requirements; note data limits.

        Reply with SHOULD BID or SHOULD SKIP, and include proposed USDC bid and ETA in hours.
        """

    async def _evaluate_and_bid(self, job: JobPostedEvent):
        """Evaluate a job, adjust for competition, and place a bid."""
        logger.info(f"Evaluating job #{job.job_id} for TikTok agent...")

        if not self.can_handle_job_type(job.job_type):
            logger.debug("Skipping job: not our type.")
            return

        if not self._matches_job(job):
            logger.info(f"Skipping job #{job.job_id}: description not TikTok-related.")
            return

        if len(self.active_jobs) >= self.max_concurrent_jobs:
            logger.warning(f"Skipping job #{job.job_id}: at capacity.")
            return

        prompt = self.get_bidding_prompt(job)

        try:
            if self.use_simple_bid or not self.llm_agent:
                decision = self._heuristic_bid_decision(job)
            else:
                response = await self.llm_agent.run(prompt)
                decision = self._parse_bid_decision(response, job)
        except Exception as e:
            logger.error(f"Error evaluating job #{job.job_id}: {e}")
            return

        decision = self._adjust_bid_for_competition(decision, job)

        logger.info(f"Decision: {'BID' if decision.should_bid else 'SKIP'} for job #{job.job_id}")
        logger.info(f"Reasoning: {decision.reasoning}")

        if decision.should_bid and self._contracts:
            await self._place_bid(job, decision)

    async def execute_job(self, job: ActiveJob) -> dict:
        logger.info(f"Executing TikTok job #{job.job_id}")
        if not self.llm_agent:
            return {"success": False, "error": "LLM agent not initialized"}

        prompt = f"""
        Execute TikTok scrape for job #{job.job_id}.
        Description: {job.description}
        Goal: collect videos matching requested hashtags/profiles; keep cost low.

        Steps:
        1) Use tiktok_scrape or tiktok_search with provided profile/hashtags.
        2) Return matched videos with URLs, captions, hashtags, metrics.
        3) Keep results concise.
        """
        try:
            response = await self.llm_agent.run(prompt)
            success = "http" in response.lower() or "tiktok.com" in response.lower()
            return {"success": success, "result": response, "job_id": job.job_id}
        except Exception as e:
            logger.error(f"TikTok job error: {e}")
            return {"success": False, "error": str(e)}


async def create_tiktok_agent() -> TikTokAgent:
    agent = TikTokAgent()
    await agent.initialize()
    return agent


async def main():
    logging.basicConfig(level=logging.INFO)
    agent = await create_tiktok_agent()
    logger.info(f"Status: {agent.get_status()}")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        logger.info("TikTok agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
