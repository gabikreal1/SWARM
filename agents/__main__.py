"""
Archive Protocol Agents - Main Entry Point

Run individual agents or the full agent system.
"""

import os
import sys
import asyncio
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_manager():
    """Run the Manager Agent server"""
    from agents.src.manager.server import run_server
    logger.info("🚀 Starting Manager Agent on port 3001...")
    run_server()


async def run_scraper():
    """Run the Scraper Agent server"""
    from agents.src.scraper.server import run_server
    logger.info("🚀 Starting Scraper Agent on port 3002...")
    run_server()


async def run_caller():
    """Run the Caller Agent server"""
    from agents.src.caller.server import run_server
    logger.info("🚀 Starting Caller Agent on port 3003...")
    run_server()


def main():
    parser = argparse.ArgumentParser(
        description="Archive Protocol Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agents manager   # Run Manager Agent
  python -m agents scraper   # Run Scraper Agent  
  python -m agents caller    # Run Caller Agent
  python -m agents all       # Run all agents (requires multiple processes)
        """
    )
    
    parser.add_argument(
        "agent",
        choices=["manager", "scraper", "caller", "all"],
        help="Which agent to run"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="Override default port for the agent"
    )
    
    args = parser.parse_args()
    
    # Set port override
    if args.port:
        if args.agent == "manager":
            os.environ["MANAGER_PORT"] = str(args.port)
        elif args.agent == "scraper":
            os.environ["SCRAPER_PORT"] = str(args.port)
        elif args.agent == "caller":
            os.environ["CALLER_PORT"] = str(args.port)
    
    # Run selected agent
    if args.agent == "manager":
        asyncio.run(run_manager())
    elif args.agent == "scraper":
        asyncio.run(run_scraper())
    elif args.agent == "caller":
        asyncio.run(run_caller())
    elif args.agent == "all":
        print("""
To run all agents, use separate terminal windows:

Terminal 1:
  python -m agents manager

Terminal 2:
  python -m agents scraper

Terminal 3:
  python -m agents caller

Or use a process manager like supervisord or Docker Compose.
        """)
        sys.exit(0)


if __name__ == "__main__":
    main()
