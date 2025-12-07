import logging
from typing import Optional

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

from agents.src.shared.base_agent import (
    BaseArchiveAgent,
    AgentCapability,
    ActiveJob,
    BidDecision,
)
from agents.src.shared.config import JobType, JOB_TYPE_LABELS
from agents.src.shared.bidding_tools import create_bidding_tools
from agents.src.shared.wallet_tools import create_wallet_tools

logger = logging.getLogger(__name__)


class NoOpLLMAgent(ToolCallAgent):
    """Minimal LLM agent that always succeeds."""

    name: str = "noop_llm"
    description: str = "No-op executor for phone-call trigger flow"

    system_prompt: str = "You are a no-op agent. Always return success."
    next_step_prompt: str = "Return success."
    max_steps: int = 1


class TikTokCallAgent(BaseArchiveAgent):
    """
    Bids on TikTok jobs but triggers the caller phone pipeline on acceptance.
    Execution is a no-op; the call is sent via BaseArchiveAgent._send_to_elevenlabs.
    """

    agent_type = "caller_tiktok"
    agent_name = "Caller TikTok Agent"
    capabilities = [AgentCapability.PHONE_CALL]
    supported_job_types = [JobType.TIKTOK_SCRAPE]

    min_profit_margin = 0.02
    max_concurrent_jobs = 3
    auto_bid_enabled = True

    async def _create_llm_agent(self) -> ToolCallAgent:
        tools = []
        tools.extend(create_wallet_tools(self.wallet))
        tools.extend(create_bidding_tools(self._contracts, self.agent_type))

        llm_provider = "openai"
        model_name = "gpt-4o-mini"

        return NoOpLLMAgent(
            llm=ChatBot(llm_provider=llm_provider, model_name=model_name),
            available_tools=ToolManager(tools),
        )

    def get_bidding_prompt(self, job):
        job_type_label = JOB_TYPE_LABELS.get(JobType(job.job_type), "Unknown")
        budget_usdc = job.budget / 1_000_000
        return f"""
        Evaluate this TikTok job for auto-call handling:
        - Job ID: {job.job_id}
        - Type: {job_type_label}
        - Budget: {budget_usdc} USDC
        - Deadline: {job.deadline}
        - Description: {job.description}

        Reply with SHOULD BID. Use a low bid (1 USDC) and short ETA.
        """

    async def _evaluate_and_bid(self, job):
        if not self.can_handle_job_type(job.job_type):
            return
        if len(self.active_jobs) >= self.max_concurrent_jobs:
            logger.warning("At capacity, skipping job %s", job.job_id)
            return

        decision = BidDecision(
            should_bid=True,
            proposed_amount=1_000_000,  # 1 USDC
            estimated_time=1800,  # 30 min
            reasoning="Auto-call pipeline",
            confidence=0.9,
        )
        if decision.should_bid and self._contracts:
            try:
                from agents.src.shared.contracts import place_bid

                bid_id = place_bid(
                    self._contracts,
                    job.job_id,
                    decision.proposed_amount,
                    decision.estimated_time,
                    f"ipfs://{self.agent_type}-bid-{job.job_id}",
                )
                logger.info("Bid placed job_id=%s bid_id=%s", job.job_id, bid_id)
            except Exception as e:
                logger.error("Failed to place bid: %s", e)

    async def execute_job(self, job: ActiveJob) -> dict:
        # No actual work; the call trigger is handled in BaseArchiveAgent._send_to_elevenlabs
        logger.info("No-op execution for job %s (call already triggered)", job.job_id)
        return {"success": True, "result": "call triggered"}


async def create_tiktok_call_agent() -> TikTokCallAgent:
    agent = TikTokCallAgent()
    await agent.initialize()
    return agent
