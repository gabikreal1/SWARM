"""
Butler Agent - Archive Protocol

The Butler Agent is the user-facing interface that:
1. Answers questions via RAG (Qdrant + Mem0)
2. Collects structured intent via slot filling
3. Posts jobs to OrderBook
4. Monitors bids and helps user select best agent
5. Tracks job execution and retrieves deliveries

This is NOT a worker agent - it posts jobs but doesn't bid on them.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List

from pydantic import Field

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

from ..shared.config import get_network, get_contract_addresses
from .tools import create_butler_tools

logger = logging.getLogger(__name__)


class ButlerLLMAgent(ToolCallAgent):
    """
    SpoonOS ToolCallAgent for the Butler.
    
    Handles LLM-driven conversation and tool calling for user interaction.
    """
    
    name: str = "butler_llm"
    description: str = "Butler AI agent for Archive Protocol - user-facing assistant"
    
    system_prompt: str = """
    You are the Butler AI for Archive Protocol, a helpful assistant that helps users:
    
    1. **Answer Questions** using RAG (rag_search):
       - Restaurant recommendations
       - Service information
       - General knowledge queries
       - Use the knowledge base first before asking for more details
    
    2. **Post Jobs** to the decentralized marketplace:
       - TikTok scraping (username, count)
       - Web scraping (url)
       - Data analysis (data_source, analysis_type)
       - Content generation (content_type, topic, length)
    
    3. **Job Management Workflow**:
       a. Use fill_slots to identify missing parameters
       b. Ask user clarifying questions (max 3 at a time)
       c. When all slots filled, confirm with user
       d. Use post_job to post to OrderBook
       e. Use get_bids to show available agents
       f. Help user evaluate bids by price/reputation
       g. Use accept_bid when user confirms
       h. Use check_job_status to monitor progress
       i. Use get_delivery to retrieve completed results
    
    4. **Natural Conversation**:
       - Be friendly and helpful
       - Explain what you're doing
       - Confirm before posting jobs or accepting bids
       - Keep user informed of progress
    
    IMPORTANT RULES:
    - ALWAYS confirm with user before posting jobs or accepting bids
    - Explain costs clearly (bids are in USDC)
    - If multiple bids, explain trade-offs (price vs delivery time vs reputation)
    - After accepting bid, let user know funds are locked in escrow
    - Check status proactively for long-running jobs
    """
    
    next_step_prompt: str = """
    Based on the conversation:
    
    - If user asks question: Try rag_search first
    - If user wants to do something: Use fill_slots to identify requirements
    - If slots incomplete: Ask clarifying questions
    - If slots complete: Summarize and ask for confirmation
    - If confirmed: Use post_job
    - After job posted: Wait briefly, then get_bids
    - With bids: Present options to user
    - User chooses: Use accept_bid
    - After accepting: Use check_job_status periodically
    - Job complete: Use get_delivery
    """
    
    max_steps: int = 20


class ButlerAgent:
    """
    Butler Agent for Archive Protocol.
    
    This is the main user interface agent - it posts jobs but doesn't execute them.
    """
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview"
    ):
        """Initialize Butler Agent"""
        self.private_key = private_key or os.getenv("NEOX_PRIVATE_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.private_key:
            raise ValueError("NEOX_PRIVATE_KEY required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required")
        
        # Create tool manager
        self.tool_manager = create_butler_tools()
        
        # Create LLM agent
        self.llm_agent = ButlerLLMAgent(
            tool_manager=self.tool_manager,
            api_key=self.openai_api_key,
            model=self.model
        )
        
        # Create chatbot interface
        self.chatbot = ChatBot(agent=self.llm_agent)
        
        # Session state
        self.conversation_history: List[Dict[str, str]] = []
        self.current_job_id: Optional[int] = None
        self.current_slots: Dict[str, Any] = {}
        
        logger.info("🤖 Butler Agent initialized")
    
    async def chat(self, message: str, user_id: str = "cli_user") -> str:
        """
        Main chat interface - send message and get response.
        
        Args:
            message: User's message
            user_id: User identifier for personalization
            
        Returns:
            Butler's response
        """
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Get response from LLM agent
        try:
            response = await self.chatbot.chat(message)
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return response
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            logger.error(f"Chat error: {e}")
            return error_msg
    
    async def post_job(
        self,
        description: str,
        tool: str,
        parameters: Dict[str, Any],
        deadline_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Post a job to OrderBook.
        
        Args:
            description: Job description
            tool: Tool/job type
            parameters: Job parameters
            deadline_hours: Deadline in hours
            
        Returns:
            Job info including job_id
        """
        try:
            result = await self.tool_manager.execute_tool(
                "post_job",
                description=description,
                tool=tool,
                parameters=parameters,
                deadline_hours=deadline_hours
            )
            
            result_data = eval(result)  # Parse JSON string
            if result_data.get("success"):
                self.current_job_id = result_data["job_id"]
            
            return result_data
            
        except Exception as e:
            logger.error(f"Failed to post job: {e}")
            return {"error": str(e)}
    
    async def get_bids(self, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get bids for a job.
        
        Args:
            job_id: Job ID (uses current_job_id if not provided)
            
        Returns:
            Bids information
        """
        job_id = job_id or self.current_job_id
        if not job_id:
            return {"error": "No job ID provided"}
        
        try:
            result = await self.tool_manager.execute_tool(
                "get_bids",
                job_id=job_id
            )
            
            return eval(result)  # Parse JSON string
            
        except Exception as e:
            logger.error(f"Failed to get bids: {e}")
            return {"error": str(e)}
    
    async def accept_bid(self, bid_id: int, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Accept a bid.
        
        Args:
            bid_id: Bid ID to accept
            job_id: Job ID (uses current_job_id if not provided)
            
        Returns:
            Acceptance confirmation
        """
        job_id = job_id or self.current_job_id
        if not job_id:
            return {"error": "No job ID provided"}
        
        try:
            result = await self.tool_manager.execute_tool(
                "accept_bid",
                job_id=job_id,
                bid_id=bid_id
            )
            
            return eval(result)  # Parse JSON string
            
        except Exception as e:
            logger.error(f"Failed to accept bid: {e}")
            return {"error": str(e)}
    
    async def check_status(self, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Check job status.
        
        Args:
            job_id: Job ID (uses current_job_id if not provided)
            
        Returns:
            Job status information
        """
        job_id = job_id or self.current_job_id
        if not job_id:
            return {"error": "No job ID provided"}
        
        try:
            result = await self.tool_manager.execute_tool(
                "check_job_status",
                job_id=job_id
            )
            
            return eval(result)  # Parse JSON string
            
        except Exception as e:
            logger.error(f"Failed to check status: {e}")
            return {"error": str(e)}
    
    async def get_delivery(self, job_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get delivery results.
        
        Args:
            job_id: Job ID (uses current_job_id if not provided)
            
        Returns:
            Delivery information
        """
        job_id = job_id or self.current_job_id
        if not job_id:
            return {"error": "No job ID provided"}
        
        try:
            result = await self.tool_manager.execute_tool(
                "get_delivery",
                job_id=job_id
            )
            
            return eval(result)  # Parse JSON string
            
        except Exception as e:
            logger.error(f"Failed to get delivery: {e}")
            return {"error": str(e)}


def create_butler_agent(
    private_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4-turbo-preview"
) -> ButlerAgent:
    """
    Factory function to create Butler Agent.
    
    Args:
        private_key: Blockchain private key
        openai_api_key: OpenAI API key
        model: LLM model to use
        
    Returns:
        Configured ButlerAgent instance
    """
    return ButlerAgent(
        private_key=private_key,
        openai_api_key=openai_api_key,
        model=model
    )
