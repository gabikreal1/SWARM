"""
Archive Protocol Agents

SpoonOS-based agents for decentralized task execution.
"""

__version__ = "0.1.0"
__author__ = "Archive Protocol"

from agents.src.manager.agent import ManagerAgent, create_manager_agent
from agents.src.scraper.agent import ScraperAgent, create_scraper_agent  
from agents.src.caller.agent import CallerAgent, create_caller_agent

__all__ = [
    "ManagerAgent",
    "ScraperAgent", 
    "CallerAgent",
    "create_manager_agent",
    "create_scraper_agent",
    "create_caller_agent",
]
