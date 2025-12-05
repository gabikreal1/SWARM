"""
Shared utilities for Archive Agents

Provides common functionality used across all agents:
- config: Network settings, contract addresses, environment config
- contracts: Smart contract interaction (OrderBook, AgentRegistry, etc.)
- a2a: Agent-to-Agent communication protocol
- neofs: NeoFS storage for decentralized proof-of-work
- wallet: Wallet management and transaction signing
- events: Blockchain event listening
- base_agent: Abstract base class for worker agents
- wallet_tools: Tools for wallet interactions
- bidding_tools: Tools for job bidding workflow
"""

from .config import *
from .contracts import *
from .a2a import *
from .neofs import *
from .wallet import *
from .events import *
from .base_agent import *
from .wallet_tools import *
from .bidding_tools import *
