"""
One-off TikTok bid script.

Scans a range of OrderBook jobs, finds TikTok-related requests, and places a
competitive low bid using the TikTok agent wallet.

Usage:
    python agents/src/tiktok/bid_once.py [start_id] [end_id]

Env:
    TIKTOK_PRIVATE_KEY (required)
    ORDERBOOK_ADDRESS, ESCROW_ADDRESS, JOB_REGISTRY_ADDRESS,
    AGENT_REGISTRY_ADDRESS, REPUTATION_TOKEN_ADDRESS, USDC_ADDRESS,
    NEOX_RPC_URL, NEOX_CHAIN_ID (already set in .env)
"""
import os
import sys
import logging

from agents.src.shared.contracts import (
    get_contracts,
    get_job,
    get_bids_for_job,
    place_bid,
)
from agents.src.shared.config import JobType


def is_tiktok_job(job_tuple) -> bool:
    """Heuristic: job tuple from get_job, index 0 is description, index 1 is job_type."""
    if not job_tuple:
        return False
    try:
        desc = (job_tuple[0] or "").lower()
        job_type = int(job_tuple[1])
        return job_type == JobType.TIKTOK_SCRAPE.value or "tiktok" in desc or "tt" in desc
    except Exception:
        return False


def main():
    logging.basicConfig(level=logging.INFO)
    start_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    end_id = int(sys.argv[2]) if len(sys.argv) > 2 else start_id + 20

    if not os.getenv("TIKTOK_PRIVATE_KEY"):
        print("TIKTOK_PRIVATE_KEY not set")
        sys.exit(1)

    contracts = get_contracts(private_key=os.getenv("TIKTOK_PRIVATE_KEY"))
    order_book = contracts.order_book

    for job_id in range(start_id, end_id + 1):
        try:
            job = get_job(contracts, job_id)
        except Exception:
            continue

        if not is_tiktok_job(job):
            continue

        desc = job[0]
        job_type = int(job[1])
        budget = int(job[2]) if len(job) > 2 else 0
        logging.info(f"Found TikTok job #{job_id}: type={job_type} budget={budget/1_000_000} USDC desc={desc}")

        # Under-cut lowest bid if exists, else bid 70% of budget
        bid_amount = int(budget * 0.7) if budget > 0 else 1_000_000
        try:
            bids = get_bids_for_job(contracts, job_id)
            if bids:
                lowest = min(b[2] for b in bids)  # amount field
                bid_amount = max(int(lowest * 0.95), 100_000)
        except Exception:
            pass

        eta_seconds = 3600  # 1 hour default
        metadata_uri = f"ipfs://tiktok-bid-{job_id}"

        try:
            tx_hash = place_bid(contracts, job_id, bid_amount, eta_seconds, metadata_uri)
            logging.info(f"Placed bid on job #{job_id}: {bid_amount/1_000_000} USDC, tx={tx_hash}")
        except Exception as e:
            logging.error(f"Failed to bid on job #{job_id}: {e}")


if __name__ == "__main__":
    main()
