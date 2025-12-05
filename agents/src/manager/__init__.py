"""
Manager Agent - Job Orchestrator

The Manager Agent orchestrates job execution by:
- Decomposing complex jobs into sub-tasks
- Coordinating worker agents (Scraper, Caller)
- Managing bids and selecting workers
- Approving deliveries and releasing payments
"""

from .tools import (
    DecomposeJobTool,
    GetBidsForJobTool,
    SelectBestBidTool,
    AcceptBidTool,
    SendA2AMessageTool,
    RequestTaskExecutionTool,
    ApproveDeliveryTool,
    GetJobDetailsTool,
    GetAgentEndpointsTool,
    get_manager_tools,
)

from .agent import ManagerAgent, create_manager_agent

from .server import app, run_server

__all__ = [
    # Tools
    "DecomposeJobTool",
    "GetBidsForJobTool",
    "SelectBestBidTool",
    "AcceptBidTool",
    "SendA2AMessageTool",
    "RequestTaskExecutionTool",
    "ApproveDeliveryTool",
    "GetJobDetailsTool",
    "GetAgentEndpointsTool",
    "get_manager_tools",
    # Agent
    "ManagerAgent",
    "create_manager_agent",
    # Server
    "app",
    "run_server",
]
