"""
TikTok Hashtag Agent for SpoonOS

Competes on TikTok scraping jobs with a low-bid strategy and filters videos
by requested hashtags.
"""

import os
import json
import base64
import asyncio
import logging
from typing import Optional

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot
import httpx

from agents.src.shared.base_agent import BaseArchiveAgent, AgentCapability, ActiveJob, BidDecision
from agents.src.shared.config import JobType, JOB_TYPE_LABELS
from agents.src.shared.events import JobPostedEvent
from agents.src.shared.wallet_tools import create_wallet_tools
from agents.src.shared.bidding_tools import create_bidding_tools
from agents.src.tiktok.tool import create_tiktok_tools
from agents.src.shared.contracts import get_bids_for_job, get_job
from agents.src.shared.neofs import get_neofs_client

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

    def __init__(self):
        super().__init__()
        self._job_metadata_cache: dict[int, dict] = {}
        self._metadata_uri_cache: dict[str, str] = {}

    def _matches_job(self, job: JobPostedEvent) -> bool:
        """Check if the job description or tags look like a TikTok scrape we can do."""
        tokens = ["tiktok", "tt", "hashtag", "profile"]
        metadata_record = self._get_job_metadata_record(job.job_id) or {}
        desc_source = job.description or metadata_record.get("description") or ""
        desc = desc_source.lower()

        registry_tags = metadata_record.get("tags") or []
        tag_list = list({*self._get_job_tags(job.job_id), *registry_tags})
        tags_joined = " ".join(tag_list).lower() if tag_list else ""

        metadata_uri = metadata_record.get("metadata_uri") or ""
        metadata_text = self._get_metadata_text(metadata_uri)

        searchable_text = " ".join(filter(None, [desc, metadata_text]))
        matched = any(tok in searchable_text for tok in tokens) or any(tok in tags_joined for tok in tokens)
        logger.info(
            "Match check job_id=%s tokens=%s desc_snip=%s tags=%s metadata_uri=%s match=%s",
            getattr(job, "job_id", None),
            tokens,
            desc[:200],
            tag_list,
            metadata_uri,
            matched,
        )
        return matched

    def _get_job_tags(self, job_id: int) -> list[str]:
        """Fetch tags from JobRegistry metadata for a given job id."""
        record = self._get_job_metadata_record(job_id) or {}
        tags = record.get("tags") or []
        return [str(t) for t in tags]

    def _get_job_metadata_record(self, job_id: int) -> dict | None:
        """Return cached job metadata (description, tags, metadataURI) from JobRegistry."""
        if job_id in self._job_metadata_cache:
            return self._job_metadata_cache[job_id]

        if not self._contracts:
            return None
        try:
            stored_job, _ = self._contracts.job_registry.functions.getJob(job_id).call()
        except Exception as e:
            logger.debug("Failed to fetch job metadata for job %s: %s", job_id, e)
            return None

        if not stored_job or not isinstance(stored_job, (list, tuple)) or len(stored_job) == 0:
            return None

        metadata = stored_job[0] if isinstance(stored_job[0], (list, tuple)) else stored_job
        record = {
            "description": metadata[2] if len(metadata) > 2 else "",
            "metadata_uri": metadata[3] if len(metadata) > 3 else "",
            "tags": metadata[4] if len(metadata) > 4 else [],
        }
        self._job_metadata_cache[job_id] = record
        return record

    def _fetch_metadata_document(self, metadata_uri: str) -> Optional[dict]:
        """Retrieve NeoFS metadata JSON referenced by metadata_uri."""
        if not metadata_uri or not metadata_uri.startswith("neofs://"):
            return None
        try:
            _, path = metadata_uri.split("://", 1)
            container_id, object_id = path.split("/", 1)
        except ValueError:
            return None

        gateway = os.getenv("NEOFS_REST_GATEWAY", "https://rest.fs.neo.org").rstrip("/")
        url = f"{gateway}/v1/objects/{container_id}/by_id/{object_id}"
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            payload_b64 = response.json().get("payload")
            if not payload_b64:
                return None
            decoded = base64.b64decode(payload_b64)
            return json.loads(decoded)
        except Exception as e:
            logger.debug("Failed to download metadata %s: %s", metadata_uri, e)
            return None

    def _get_metadata_text(self, metadata_uri: str) -> str:
        """Return cached flattened metadata JSON for keyword matching."""
        if not metadata_uri:
            return ""
        if metadata_uri in self._metadata_uri_cache:
            return self._metadata_uri_cache[metadata_uri]

        document = self._fetch_metadata_document(metadata_uri)
        if not isinstance(document, dict):
            self._metadata_uri_cache[metadata_uri] = ""
            return ""

        try:
            text = json.dumps(document, separators=(",", ":")).lower()
        except Exception:
            text = ""
        self._metadata_uri_cache[metadata_uri] = text
        return text

    def log_historical_jobs(self, from_block: int = 0, to_block: str | int = "latest"):
        """Fetch historical JobPosted logs and log match/non-match."""
        if not self._contracts:
            logger.warning("No contracts loaded; cannot fetch historical jobs.")
            return
        try:
            logs = (
                self._contracts.order_book.events.JobPosted()
                .get_logs(from_block=from_block, to_block=to_block)
            )
            if not logs:
                logger.info("No JobPosted logs found in range %s-%s", from_block, to_block)
                return
            for ev in logs:
                args = ev["args"]
                job = JobPostedEvent(
                    job_id=args.get("jobId", args.get("id", 0)),
                    client=args.get("client", args.get("poster", "")),
                    job_type=args.get("jobType", 0),
                    budget=args.get("budget", 0),
                    deadline=args.get("deadline", 0),
                    description=args.get("description", ""),
                    block_number=ev["blockNumber"],
                    tx_hash=ev["transactionHash"].hex() if ev["transactionHash"] else "",
                )
                match = self._matches_job(job)
                logger.info(
                    "Historical JobPosted id=%s type=%s budget=%s match=%s desc=%s tx=%s",
                    job.job_id,
                    job.job_type,
                    job.budget,
                    match,
                    (job.description or "")[:200],
                    job.tx_hash,
                )
                # Also log current on-chain job state/bids if available
                try:
                    state, bids = self._contracts.order_book.functions.getJob(job.job_id).call()
                    logger.info(
                        "JobState id=%s poster=%s status=%s accepted_bid=%s has_dispute=%s bids=%s",
                        job.job_id,
                        state[0],
                        state[1],
                        state[2],
                        state[4],
                        len(bids),
                    )
                except Exception as e:
                    logger.debug("Unable to fetch job state for id=%s: %s", job.job_id, e)
        except Exception as e:
            logger.error("Failed to fetch historical jobs: %s", e)

    def _log_job_received(self, job: JobPostedEvent):
        logger.info(
            "JobPosted received | id=%s type=%s budget=%s deadline=%s desc=%s",
            job.job_id,
            job.job_type,
            job.budget,
            job.deadline,
            (job.description or "")[:200],
        )

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

    async def _build_metadata_uri(self, job: JobPostedEvent, decision) -> str:
        """
        Upload lightweight bid metadata to NeoFS and return a URI.
        Falls back to ipfs:// placeholder on failure.
        """
        try:
            neofs = get_neofs_client()
            payload = {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "description": job.description,
                "budget": job.budget,
                "deadline": job.deadline,
                "proposed_amount": decision.proposed_amount,
                "estimated_time": decision.estimated_time,
                "agent": self.agent_name,
                "agent_type": self.agent_type,
            }
            result = await neofs.upload_json(
                payload,
                filename=f"bid-{job.job_id}.json",
                additional_attributes=None,
                container_id=os.getenv("NEOFS_CONTAINER_ID"),
            )
            await neofs.close()
            uri = f"neofs://{result.container_id}/{result.object_id}"
            logger.info("Uploaded bid metadata to NeoFS: %s", uri)
            return uri
        except Exception as e:
            logger.warning("NeoFS metadata upload failed, falling back to ipfs:// placeholder: %s", e)
            return f"ipfs://{self.agent_type}-bid-{job.job_id}"

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
        self._log_job_received(job)
        logger.info(f"Evaluating job #{job.job_id} for TikTok agent...")

        if not self.can_handle_job_type(job.job_type):
            logger.info("Skipping job #%s: not our job type (%s)", job.job_id, job.job_type)
            return

        if not self._matches_job(job):
            logger.info(f"Skipping job #{job.job_id}: description not TikTok-related.")
            return

        if len(self.active_jobs) >= self.max_concurrent_jobs:
            logger.warning(f"Skipping job #{job.job_id}: at capacity.")
            return

        # Auto-bid 1 USDC whenever we match a TikTok job
        logger.info("Match confirmed for job #%s, preparing auto-bid", job.job_id)
        decision = BidDecision(
            should_bid=True,
            proposed_amount=1_000_000,  # 1 USDC
            estimated_time=3600,  # default 1 hour
            reasoning="Auto-match TikTok job with fixed 1 USDC bid",
            confidence=0.9,
        )
        logger.info("Auto-bidding 1 USDC for job #%s", job.job_id)

        if decision.should_bid and self._contracts:
            metadata_uri = await self._build_metadata_uri(job, decision)
            # place bid with custom metadata URI
            try:
                logger.info(
                    "Attempting bid job_id=%s amount=%s eta=%s metadata=%s",
                    job.job_id,
                    decision.proposed_amount,
                    decision.estimated_time,
                    metadata_uri,
                )
                from agents.src.shared.contracts import place_bid  # local import to avoid cycle
                bid_id = place_bid(
                    self._contracts,
                    job.job_id,
                    decision.proposed_amount,
                    decision.estimated_time,
                    metadata_uri,
                )
                logger.info("Bid placed job_id=%s bid_id=%s", job.job_id, bid_id)
            except Exception as e:
                logger.error("Failed to place bid on job %s: %s", job.job_id, e)
        elif decision.should_bid and not self._contracts:
            logger.error("Contracts not initialized; cannot bid on job #%s", job.job_id)

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
