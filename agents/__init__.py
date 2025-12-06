"""
Archive Protocol Agents

SpoonOS-based agents for decentralized task execution.
"""

__version__ = "0.1.0"
__author__ = "Archive Protocol"

# Lazy-load agent types to avoid import-time failures when optional deps are missing.
def __getattr__(name):
    if name in {"ManagerAgent", "create_manager_agent"}:
        from agents.src.manager.agent import ManagerAgent, create_manager_agent
        return ManagerAgent if name == "ManagerAgent" else create_manager_agent
    if name in {"ScraperAgent", "create_scraper_agent"}:
        from agents.src.scraper.agent import ScraperAgent, create_scraper_agent
        return ScraperAgent if name == "ScraperAgent" else create_scraper_agent
    if name in {"CallerAgent", "create_caller_agent"}:
        from agents.src.caller.agent import CallerAgent, create_caller_agent
        return CallerAgent if name == "CallerAgent" else create_caller_agent
    raise AttributeError(name)

__all__ = [
    "ManagerAgent",
    "ScraperAgent",
    "CallerAgent",
    "create_manager_agent",
    "create_scraper_agent",
    "create_caller_agent",
]
