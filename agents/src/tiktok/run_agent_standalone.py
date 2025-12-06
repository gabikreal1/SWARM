import os
import sys
import asyncio
import logging
from pathlib import Path

# Ensure repo root on path
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))
from agents.src.tiktok.agent import create_tiktok_agent


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    agent = await create_tiktok_agent()
    # Start the agent (event listener + bidding loop)
    await agent.start()
    logging.info(f"TikTok agent running: {agent.get_status()}")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        logging.info("TikTok agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
