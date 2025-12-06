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
    You are the Butler AI for Archive Protocol.
    
    ### MANDATORY WORKFLOW
    For EVERY user request, you must follow this sequence:
    
    1. **CHECK KNOWLEDGE (RAG)**:
       - Call `rag_search` to see if you have context or if this is a simple question.
       - If the tool says "Match found", answer the user and STOP.
       - If the tool says "No match", PROCEED to Step 2 (Evaluate Intent).
       
    2. **EVALUATE INTENT**:
       - **DECISION POINT**:
         - If the user clearly wants to perform a task (scrape, analyze, etc.) -> Call `fill_slots`.
         - If the user's intent is unclear or looks like a question you don't know -> ASK for clarification and STOP.
       
       - **IF CALLING `fill_slots`**:
         - If the tool says "Missing slots", ASK the user the questions provided and STOP.
         - If the tool says "Ready", SUMMARIZE the job and ASK for confirmation. STOP.
       
    3. **POST JOB**:
       - ONLY after the user explicitly confirms "Yes, post it", call `post_job`.
       
    4. **POLL BIDS**:
       - Immediately after posting, call `get_bids` to show initial status.
       - Present the bids to the user and STOP.
       
    ### STOPPING RULES
    - If you generate a text response to the user, you MUST STOP.
    - Do NOT loop. Do NOT call `fill_slots` repeatedly without user input.
    """
    
    next_step_prompt: str = """
    Determine the next step based on the workflow:
    1. Start -> `rag_search`
    2. RAG found info -> Answer -> STOP
    3. RAG no info & Job Intent -> `fill_slots`
    4. RAG no info & Unclear -> Ask Clarification -> STOP
    5. Slots missing -> Ask User -> STOP
    6. Slots ready -> Ask Confirmation -> STOP
    7. Confirmed -> `post_job`
    8. Posted -> `get_bids` -> STOP
    """
    
    max_steps: int = 10

    def _should_finish_execution(self, llm_response: Any) -> bool:
        """
        Stop execution if the LLM generated a text response for the user.
        """
        # If there are tool calls, we must continue to execute them
        if hasattr(llm_response, "tool_calls") and llm_response.tool_calls:
            return False
            
        # If there is content (text response), we must stop and show it to the user
        # Even if content is empty string, if no tool calls, we should stop.
        return True


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
        
        # Create LLM client (ChatBot)
        self.llm_client = ChatBot(
            model_name=self.model,
            api_key=self.openai_api_key,
            llm_provider="openai"
        )
        
        # Create LLM agent
        # Note: 'avaliable_tools' is the field name in spoon-ai-sdk (typo in library)
        self.llm_agent = ButlerLLMAgent(
            avaliable_tools=self.tool_manager,
            llm=self.llm_client
        )
        
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
            # Use run() instead of chatbot.chat()
            response = await self.llm_agent.run(message)
            
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
