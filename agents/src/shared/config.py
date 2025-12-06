"""
Configuration management for Archive Agents
"""

import os
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class NetworkConfig:
    """Blockchain network configuration"""
    rpc_url: str
    chain_id: int
    explorer_url: str


@dataclass
class ContractAddresses:
    """Deployed contract addresses"""
    order_book: str
    escrow: str
    job_registry: str
    agent_registry: str
    reputation_token: str
    usdc: str


@dataclass
class AgentEndpoints:
    """A2A endpoint URLs for each agent"""
    manager: str
    scraper: str
    caller: str


# Network configurations
NEOX_TESTNET = NetworkConfig(
    rpc_url=os.getenv("NEOX_RPC_URL", "https://testnet.rpc.banelabs.org"),
    chain_id=12227332,
    explorer_url="https://xt4scan.ngd.network",
)

NEOX_MAINNET = NetworkConfig(
    rpc_url="https://mainnet-1.rpc.banelabs.org",
    chain_id=47763,
    explorer_url="https://xexplorer.neo.org",
)


def get_network() -> NetworkConfig:
    """Get the current network configuration based on environment"""
    chain_id = int(os.getenv("NEOX_CHAIN_ID", "12227332"))
    return NEOX_MAINNET if chain_id == 47763 else NEOX_TESTNET


def get_contract_addresses() -> ContractAddresses:
    """Get contract addresses from environment or deployment file"""
    # Try env vars first
    order_book = os.getenv("ORDERBOOK_ADDRESS")
    
    # If not in env, try loading from deployment file
    if not order_book:
        import json
        from pathlib import Path
        deployment_file = Path(__file__).parent.parent.parent.parent / "contracts" / "deployments" / "neox-testnet-12227332.json"
        if deployment_file.exists():
            with open(deployment_file) as f:
                data = json.load(f)
                return ContractAddresses(
                    order_book=data["contracts"]["OrderBook"],
                    escrow=data["contracts"]["Escrow"],
                    job_registry=data["contracts"]["JobRegistry"],
                    agent_registry=data["contracts"]["AgentRegistry"],
                    reputation_token=data["contracts"]["ReputationToken"],
                    usdc=data["usdc"],
                )
    
    return ContractAddresses(
        order_book=os.getenv("ORDERBOOK_ADDRESS", ""),
        escrow=os.getenv("ESCROW_ADDRESS", ""),
        job_registry=os.getenv("JOB_REGISTRY_ADDRESS", ""),
        agent_registry=os.getenv("AGENT_REGISTRY_ADDRESS", ""),
        reputation_token=os.getenv("REPUTATION_TOKEN_ADDRESS", ""),
        usdc=os.getenv("USDC_ADDRESS", ""),
    )


def get_agent_endpoints() -> AgentEndpoints:
    """Get agent A2A endpoints from environment"""
    return AgentEndpoints(
        manager=os.getenv("MANAGER_ENDPOINT", "http://localhost:3001"),
        scraper=os.getenv("SCRAPER_ENDPOINT", "http://localhost:3002"),
        caller=os.getenv("CALLER_ENDPOINT", "http://localhost:3003"),
    )


class JobType(IntEnum):
    """Job types matching smart contract enum"""
    TIKTOK_SCRAPE = 0
    WEB_SCRAPE = 1
    CALL_VERIFICATION = 2
    DATA_ANALYSIS = 3
    COMPOSITE = 4


JOB_TYPE_LABELS = {
    JobType.TIKTOK_SCRAPE: "TikTok Scrape",
    JobType.WEB_SCRAPE: "Web Scrape",
    JobType.CALL_VERIFICATION: "Call Verification",
    JobType.DATA_ANALYSIS: "Data Analysis",
    JobType.COMPOSITE: "Composite Job",
}


# Agent capabilities
AGENT_CAPABILITIES = {
    "MANAGER": ["job_decomposition", "agent_coordination", "result_aggregation"],
    "SCRAPER": ["tiktok_scrape", "web_scrape", "data_extraction"],
    "CALLER": ["phone_call", "voice_verification", "reservation_booking"],
}


def get_private_key(agent_type: str) -> Optional[str]:
    """Get the private key for a specific agent type"""
    key_map = {
        "butler": "NEOX_PRIVATE_KEY",  # User/Butler wallet
        "worker": "WORKER_PRIVATE_KEY",  # Generic worker
        "manager": "MANAGER_PRIVATE_KEY",
        "scraper": "SCRAPER_PRIVATE_KEY",
        "caller": "CALLER_PRIVATE_KEY",
    }
    env_var = key_map.get(agent_type.lower())
    return os.getenv(env_var) if env_var else None
