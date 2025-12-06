"""
Butler Agent Tools

Tools for the Butler to:
- Query RAG (Qdrant + Mem0)
- Fill slots with slot_questioning
- Post jobs to OrderBook
- Monitor job status and deliveries
- Retrieve results from NeoFS
"""

import os
import json
import time
from typing import Any, Optional, Dict, List
from pydantic import Field

from spoon_ai.tools.base import BaseTool
from spoon_ai.tools import ToolManager

# Import shared tools
from ..shared.contracts import get_contracts, post_job, get_bids_for_job, accept_bid, get_job_status
from ..shared.neofs import get_neofs_client
from ..shared.slot_questioning import SlotFiller


class RAGSearchTool(BaseTool):
    """
    Search knowledge base (Qdrant + Mem0) for relevant information.
    """
    name: str = "rag_search"
    description: str = """
    Search the knowledge base for relevant information to answer user questions.
    
    Use this when the user asks informational questions that might be answered
    from existing knowledge (restaurants, services, general info).
    
    Returns: List of relevant knowledge items with context.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "user_id": {
                "type": "string",
                "description": "User ID for personalized results (optional)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default 5)"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, user_id: str = "anonymous", limit: int = 5) -> str:
        """Search RAG knowledge base"""
        try:
            from qdrant_client import QdrantClient
            from mem0 import MemoryClient
            
            # Qdrant search
            qdrant = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY")
            )
            
            # Mem0 search
            mem0 = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
            
            results = {
                "query": query,
                "qdrant_results": [],
                "mem0_results": [],
            }
            
            # Try Qdrant
            try:
                # Placeholder: In production, this would be real search results.
                # For now, return empty to simulate "no match" unless query contains "test"
                if "test" in query.lower():
                    results["qdrant_results"] = ["This is a test result from Qdrant."]
                else:
                    results["qdrant_results"] = []
            except Exception as e:
                results["qdrant_error"] = str(e)
            
            # Try Mem0
            try:
                mem_results = mem0.search(query, user_id=user_id, limit=limit)
                if mem_results:
                    results["mem0_results"] = [m.get("memory") for m in mem_results if "memory" in m]
            except Exception as e:
                results["mem0_error"] = str(e)
            
            if results["qdrant_results"] or results["mem0_results"]:
                results["status"] = "match"
                results["instruction"] = "Use the information above to answer the user's question. Do NOT call any more tools. STOP."
            else:
                results["status"] = "no_match"
                results["instruction"] = "No relevant info found in knowledge base. DECIDE: If user wants a job -> `fill_slots`. If unclear -> Ask user to clarify. STOP."
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"RAG search failed: {str(e)}"})


class SlotFillingTool(BaseTool):
    """
    Fill missing slots for job posting using slot_questioning.
    """
    name: str = "fill_slots"
    description: str = """
    Analyze user request and identify missing required parameters (slots).
    
    Use this when the user wants to post a job but hasn't provided all details.
    Returns: Missing slots and suggested clarifying questions.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "The user's request"
            },
            "current_slots": {
                "type": "object",
                "description": "Already collected slot values"
            },
            "candidate_tools": {
                "type": "array",
                "description": "Available tools/job types",
                "items": {
                    "type": "object"
                }
            }
        },
        "required": ["user_message"]
    }
    
    async def execute(
        self, 
        user_message: str, 
        current_slots: Optional[Dict] = None,
        candidate_tools: Optional[List] = None
    ) -> str:
        """Fill slots using SlotFiller"""
        try:
            if candidate_tools is None:
                candidate_tools = [
                    {"name": "tiktok_scrape", "required_params": ["username", "count"]},
                    {"name": "web_scrape", "required_params": ["url"]},
                    {"name": "data_analysis", "required_params": ["data_source", "analysis_type"]},
                ]
            
            current_slots = current_slots or {}
            
            # Try to use SlotFiller
            try:
                filler = SlotFiller(user_id="butler")
                missing_slots, questions, chosen_tool = filler.fill(
                    user_message=user_message,
                    current_slots=current_slots,
                    candidate_tools=candidate_tools
                )
                
                result = {
                    "tool": chosen_tool,
                    "current_slots": current_slots,
                    "missing_slots": missing_slots,
                    "questions": questions,
                    "ready": len(missing_slots) == 0
                }
                
                if not result["ready"]:
                    result["instruction"] = "CRITICAL: You MUST ask the user the questions in the 'questions' list. Do NOT call this tool again until the user responds. OUTPUT THE QUESTIONS NOW."
                else:
                    result["instruction"] = "Slots are complete. Summarize the job details to the user and ask for confirmation to post."
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                # Fallback to basic extraction
                return json.dumps({
                    "error": f"SlotFiller unavailable: {e}",
                    "fallback": "basic",
                    "message": "Please provide job details manually"
                })
                
        except Exception as e:
            return json.dumps({"error": str(e)})


class PostJobTool(BaseTool):
    """
    Post a job to the OrderBook with NeoFS metadata.
    """
    name: str = "post_job"
    description: str = """
    Post a job to the blockchain OrderBook after collecting all required information.
    
    This will:
    1. Upload job metadata to NeoFS
    2. Post job to OrderBook smart contract
    3. Return job ID for tracking
    
    Use after slots are filled and user confirms.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Job description"
            },
            "tool": {
                "type": "string",
                "description": "Tool/job type (e.g., tiktok_scrape)"
            },
            "parameters": {
                "type": "object",
                "description": "Job parameters as key-value pairs"
            },
            "deadline_hours": {
                "type": "integer",
                "description": "Deadline in hours from now (default 24)"
            }
        },
        "required": ["description", "tool", "parameters"]
    }
    
    async def execute(
        self,
        description: str,
        tool: str,
        parameters: Dict[str, Any],
        deadline_hours: int = 24
    ) -> str:
        """Post job to OrderBook"""
        try:
            contracts = get_contracts(os.getenv("NEOX_PRIVATE_KEY"))
            neofs = get_neofs_client()
            
            # 1. Create job metadata
            metadata = {
                "tool": tool,
                "parameters": parameters,
                "poster": contracts.account.address,
                "posted_at": time.time(),
                "requirements": {
                    "quality": "high",
                    "format": "json",
                    "delivery_time": f"{deadline_hours}h"
                }
            }
            
            # 2. Upload to NeoFS
            print(f"📤 Uploading job metadata to NeoFS...")
            metadata_json = json.dumps(metadata, indent=2)
            
            # Use NeoFS client to upload
            from ..shared.neofs import upload_object
            object_id = upload_object(
                content=metadata_json,
                attributes={
                    "type": "job_metadata",
                    "tool": tool,
                    "poster": contracts.account.address
                },
                filename=f"job_{int(time.time())}.json"
            )
            
            if not object_id:
                return json.dumps({"error": "Failed to upload metadata to NeoFS"})
            
            metadata_uri = f"neofs://{os.getenv('NEOFS_CONTAINER_ID')}/{object_id}"
            print(f"✅ Metadata uploaded: {metadata_uri}")
            
            # 3. Post to blockchain
            tags = [tool]
            deadline = int(time.time()) + (deadline_hours * 3600)
            
            job_id = post_job(
                contracts,
                description=description,
                metadata_uri=metadata_uri,
                tags=tags,
                deadline=deadline
            )
            
            print(f"✅ Job posted! Job ID: {job_id}")
            
            return json.dumps({
                "success": True,
                "job_id": job_id,
                "metadata_uri": metadata_uri,
                "tags": tags,
                "deadline": deadline,
                "instruction": "Job posted successfully. Now call `get_bids` with the job_id to check for initial offers."
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to post job: {str(e)}"})


class GetBidsTool(BaseTool):
    """
    Get bids for a job.
    """
    name: str = "get_bids"
    description: str = """
    Retrieve all bids for a specific job.
    
    Use after posting a job to see which agents have bid.
    Returns: List of bids with prices, agents, and delivery times.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            }
        },
        "required": ["job_id"]
    }
    
    async def execute(self, job_id: int) -> str:
        """Get bids for job"""
        try:
            contracts = get_contracts(os.getenv("NEOX_PRIVATE_KEY"))
            bids = get_bids_for_job(contracts, job_id)
            
            formatted_bids = []
            for bid in bids:
                # Bid: (id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt)
                formatted_bids.append({
                    "bid_id": bid[0],
                    "bidder": bid[2],
                    "price_usdc": bid[3] / 1e6,  # Convert from micro USDC
                    "delivery_time_hours": bid[4] / 3600,
                    "reputation": bid[5],
                    "accepted": bid[8]
                })
            
            # Sort by price
            formatted_bids.sort(key=lambda x: x["price_usdc"])
            
            return json.dumps({
                "job_id": job_id,
                "total_bids": len(formatted_bids),
                "bids": formatted_bids,
                "best_bid": formatted_bids[0] if formatted_bids else None,
                "instruction": "Present these bids to the user. Ask which one they want to accept (or if they want to wait). STOP."
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get bids: {str(e)}"})


class AcceptBidTool(BaseTool):
    """
    Accept a bid for a job.
    """
    name: str = "accept_bid"
    description: str = """
    Accept a specific bid for a job, locking funds in escrow.
    
    Use after reviewing bids and getting user confirmation.
    The agent will then start working on the job.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            },
            "bid_id": {
                "type": "integer",
                "description": "The bid ID to accept"
            }
        },
        "required": ["job_id", "bid_id"]
    }
    
    async def execute(self, job_id: int, bid_id: int) -> str:
        """Accept a bid"""
        try:
            contracts = get_contracts(os.getenv("NEOX_PRIVATE_KEY"))
            
            tx_hash = accept_bid(
                contracts,
                job_id=job_id,
                bid_id=bid_id,
                response_uri=""
            )
            
            return json.dumps({
                "success": True,
                "job_id": job_id,
                "bid_id": bid_id,
                "tx_hash": tx_hash,
                "message": "Bid accepted! Funds locked in escrow. Agent will start work."
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to accept bid: {str(e)}"})


class CheckJobStatusTool(BaseTool):
    """
    Check the status of a job.
    """
    name: str = "check_job_status"
    description: str = """
    Check the current status of a job (Open, InProgress, Completed, Cancelled).
    
    Use to monitor job progress or check if delivery is complete.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            }
        },
        "required": ["job_id"]
    }
    
    async def execute(self, job_id: int) -> str:
        """Check job status"""
        try:
            contracts = get_contracts(os.getenv("NEOX_PRIVATE_KEY"))
            
            job_state, bids = contracts.order_book.functions.getJob(job_id).call()
            
            # JobState: (poster, status, acceptedBidId, deliveryProof, hasDispute)
            status_names = ["Open", "InProgress", "Completed", "Cancelled"]
            status = status_names[job_state[1]] if job_state[1] < len(status_names) else "Unknown"
            
            result = {
                "job_id": job_id,
                "status": status,
                "poster": job_state[0],
                "accepted_bid_id": job_state[2],
                "has_delivery": job_state[3] != b'\x00' * 32,
                "has_dispute": job_state[4]
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to check status: {str(e)}"})


class GetDeliveryTool(BaseTool):
    """
    Get delivery results from NeoFS.
    """
    name: str = "get_delivery"
    description: str = """
    Download and retrieve job delivery results from NeoFS.
    
    Use when job is completed to get the actual results/data.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            }
        },
        "required": ["job_id"]
    }
    
    async def execute(self, job_id: int) -> str:
        """Get delivery from NeoFS"""
        try:
            contracts = get_contracts(os.getenv("NEOX_PRIVATE_KEY"))
            
            # Get job details
            job_state, bids = contracts.order_book.functions.getJob(job_id).call()
            
            # Find accepted bid
            accepted_bid_id = job_state[2]
            accepted_bid = None
            
            for bid in bids:
                if bid[0] == accepted_bid_id:
                    accepted_bid = bid
                    break
            
            if not accepted_bid:
                return json.dumps({"error": "No accepted bid found"})
            
            # In production, the delivery URI would be in the bid's responseURI or metadata
            # For now, return placeholder
            return json.dumps({
                "job_id": job_id,
                "status": "completed",
                "message": "Delivery retrieval from NeoFS to be implemented",
                "bid_id": accepted_bid_id
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get delivery: {str(e)}"})


def create_butler_tools() -> ToolManager:
    """Create and register all Butler tools"""
    tools = [
        # RAG and slot filling
        RAGSearchTool(),
        SlotFillingTool(),
        
        # Job posting and management
        PostJobTool(),
        GetBidsTool(),
        AcceptBidTool(),
        CheckJobStatusTool(),
        GetDeliveryTool(),
    ]
    
    return ToolManager(tools=tools)
