"""
Register the TikTok scraper agent on AgentRegistry.

Uses env:
- TIKTOK_PRIVATE_KEY: private key for signing
- AGENT_REGISTRY_ADDRESS, ORDERBOOK_ADDRESS, ESCROW_ADDRESS, JOB_REGISTRY_ADDRESS,
  REPUTATION_TOKEN_ADDRESS, USDC_ADDRESS, NEOX_RPC_URL, NEOX_CHAIN_ID
"""
import os
import sys
import logging

from agents.src.shared.contracts import get_contracts, register_agent


def main():
    logging.basicConfig(level=logging.INFO)
    name = os.getenv("TIKTOK_AGENT_NAME", "TikTok Hashtag Agent")
    endpoint = os.getenv("TIKTOK_AGENT_ENDPOINT", "http://localhost:3002")
    capabilities = ["tiktok_scrape", "hashtag_filter"]

    contracts = get_contracts(private_key=os.getenv("TIKTOK_PRIVATE_KEY"))
    tx_hash = register_agent(contracts, name=name, endpoint=endpoint, capabilities=capabilities)
    print(f"Register tx sent: {tx_hash}")


if __name__ == "__main__":
    if not os.getenv("TIKTOK_PRIVATE_KEY"):
        print("TIKTOK_PRIVATE_KEY not set")
        sys.exit(1)
    main()
