"""
Quick runner for the TikTok agent using the shared agent stack.

Usage:
  python agents/src/tiktok/run_agent.py

Env required:
  TIKTOK_PRIVATE_KEY       -- funded key on Neo X testnet
  NEOX_RPC_URL, NEOX_CHAIN_ID
  ORDERBOOK_ADDRESS, AGENT_REGISTRY_ADDRESS, JOB_REGISTRY_ADDRESS,
  ESCROW_ADDRESS, REPUTATION_TOKEN_ADDRESS, USDC_ADDRESS

Optional:
  TIKTOK_SIMPLE_BID=1 (default) to use heuristic low bid
"""
import asyncio
import logging
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.src.tiktok.agent import create_tiktok_agent


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    agent = await create_tiktok_agent()
    status = agent.get_status()
    logging.info(f"TikTok agent ready: {status}")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        logging.info("TikTok agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
