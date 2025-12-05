"""
Manager Agent Tools

Tools for job orchestration, worker coordination, and result aggregation.
The Manager Agent:
- Decomposes complex jobs into sub-tasks
- Reviews bids from workers and selects the best ones
- Accepts bids and releases escrow
- Finalizes jobs and approves deliveries
"""

import json
import hashlib
import httpx
from typing import Any, Optional
from pydantic import Field

from spoon_ai.tools.base import BaseTool

from ..shared.config import JobType, JOB_TYPE_LABELS, get_agent_endpoints
from ..shared.wallet import AgentWallet
from ..shared.a2a import A2AMessage, A2AMethod, sign_message
from ..shared.contracts import get_contracts, post_job
from ..shared.booking import analyze_slots
from ..shared.bevec import BeVecClient, VectorRecord
from ..shared.embedding import embed_text
from ..shared.neofs import get_neofs_client


# ==============================================================================
# JOB DECOMPOSITION TOOLS
# ==============================================================================

class DecomposeJobTool(BaseTool):
    """
    Decompose a complex job into sub-tasks.
    """
    name: str = "decompose_job"
    description: str = """
    Decompose a complex user request into specific sub-tasks that can be executed by worker agents.
    Use this when you receive a composite job that requires multiple steps.
    
    Analyze the job description and identify:
    - TikTok/social media scraping tasks
    - Web search and scraping tasks
    - Phone call verification tasks
    - Data analysis tasks
    
    Returns a structured list of sub-tasks with their types and parameters.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_description": {
                "type": "string",
                "description": "The full job description to decompose"
            },
            "job_type": {
                "type": "integer",
                "description": "Job type enum (0=TIKTOK_SCRAPE, 1=WEB_SCRAPE, 2=CALL_VERIFICATION, 3=DATA_ANALYSIS, 4=COMPOSITE)"
            },
            "budget": {
                "type": "integer",
                "description": "Total budget in USDC micro-units"
            }
        },
        "required": ["job_description", "job_type"]
    }
    
    async def execute(
        self, 
        job_description: str, 
        job_type: int,
        budget: int = 0
    ) -> str:
        """Decompose a job into sub-tasks"""
        sub_tasks = []
        
        # Keywords for different task types
        tiktok_keywords = ["tiktok", "viral", "trending", "social media", "video", "reels"]
        web_keywords = ["website", "search", "google", "web", "online", "find"]
        call_keywords = ["call", "phone", "book", "reserve", "reservation", "verify", "confirm"]
        
        job_lower = job_description.lower()
        budget_per_task = 0
        
        # Detect required sub-tasks
        if any(kw in job_lower for kw in tiktok_keywords):
            sub_tasks.append({
                "task_type": "TIKTOK_SCRAPE",
                "job_type_id": JobType.TIKTOK_SCRAPE.value,
                "description": f"Scrape TikTok for: {job_description}",
                "parameters": {
                    "search_query": self._extract_search_query(job_description),
                    "max_results": 10
                }
            })
        
        if any(kw in job_lower for kw in web_keywords):
            sub_tasks.append({
                "task_type": "WEB_SCRAPE",
                "job_type_id": JobType.WEB_SCRAPE.value,
                "description": f"Search web for: {job_description}",
                "parameters": {
                    "search_query": self._extract_search_query(job_description)
                }
            })
        
        if any(kw in job_lower for kw in call_keywords):
            sub_tasks.append({
                "task_type": "CALL_VERIFICATION",
                "job_type_id": JobType.CALL_VERIFICATION.value,
                "description": f"Make verification call: {job_description}",
                "parameters": {
                    "purpose": "verification",
                    "script_hint": self._generate_call_script(job_description)
                }
            })
        
        # Default to data analysis if no specific tasks detected
        if not sub_tasks:
            sub_tasks.append({
                "task_type": "DATA_ANALYSIS",
                "job_type_id": JobType.DATA_ANALYSIS.value,
                "description": job_description,
                "parameters": {}
            })
        
        # Allocate budget per task
        if budget > 0 and sub_tasks:
            budget_per_task = budget // len(sub_tasks)
            for task in sub_tasks:
                task["allocated_budget"] = budget_per_task
        
        return json.dumps({
            "success": True,
            "original_job": job_description,
            "original_type": JOB_TYPE_LABELS.get(job_type, "UNKNOWN"),
            "sub_tasks": sub_tasks,
            "total_tasks": len(sub_tasks),
            "budget_allocation": budget_per_task if budget > 0 else "not_set"
        }, indent=2)
    
    def _extract_search_query(self, description: str) -> str:
        """Extract a search query from the job description"""
        keywords = ["find", "search", "look for", "get", "about"]
        for kw in keywords:
            if kw in description.lower():
                idx = description.lower().find(kw)
                return description[idx:].strip()
        return description
    
    def _generate_call_script(self, description: str) -> str:
        """Generate a call script hint"""
        return f"Verify information about: {description}"


# ==============================================================================
# BOOKING / RAG TOOLS
# ==============================================================================


class CollectBookingRequirementsTool(BaseTool):
    """Identify missing booking slots and generate questions for the user."""

    name: str = "collect_booking_requirements"
    description: str = """
    Given a user prompt and any known slots, determine which booking details are missing
    (location, date, time, party_size, budget, cuisine). Returns missing slots and
    questions to ask the user.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "User request"},
            "slots": {"type": "object", "description": "Known slot values"},
        },
        "required": ["prompt"],
    }

    async def execute(self, prompt: str, slots: dict | None = None) -> str:
        analysis = analyze_slots(prompt, slots or {})
        return json.dumps(
            {
                "success": True,
                "slots": analysis.slots,
                "missing_slots": analysis.missing_slots,
                "questions": analysis.questions,
                "tags": analysis.tags,
            },
            indent=2,
        )


class BuildBookingContextTool(BaseTool):
    """Retrieve similar experiences and playbooks from beVec."""

    name: str = "build_booking_context"
    description: str = """
    Use beVec to retrieve prior experiences and playbooks relevant to the booking request.
    Requires BEVEC_ENDPOINT and OPENAI_API_KEY to be configured.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "User request"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags to filter vectors (e.g., location, cuisine)",
            },
            "top_k_experiences": {"type": "integer", "default": 4},
            "top_k_playbooks": {"type": "integer", "default": 2},
        },
        "required": ["prompt"],
    }

    def __init__(self, vector_client: Optional[BeVecClient]):
        super().__init__()
        self._vector_client = vector_client

    async def execute(
        self,
        prompt: str,
        tags: list[str] | None = None,
        top_k_experiences: int = 4,
        top_k_playbooks: int = 2,
    ) -> str:
        if not self._vector_client:
            return json.dumps({"success": False, "error": "beVec not configured"})

        query_text = f"Restaurant booking intent: {prompt}\nTags: {', '.join(tags or [])}"
        try:
            vector = await embed_text(query_text)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Embedding failed: {e}"})

        try:
            experiences = [r.__dict__ for r in await self._vector_client.query(
                collection="user_experiences",
                vector=vector,
                top_k=top_k_experiences,
                tags=tags or ["restaurant", "booking"],
            )]
        except Exception as e:
            experiences = []
            error = f"Experience query failed: {e}"
            return json.dumps({"success": False, "error": error})

        try:
            playbooks = [r.__dict__ for r in await self._vector_client.query(
                collection="booking_playbooks",
                vector=vector,
                top_k=top_k_playbooks,
                tags=["booking"],
            )]
        except Exception as e:
            playbooks = []
            return json.dumps({"success": False, "error": f"Playbook query failed: {e}"})

        return json.dumps(
            {
                "success": True,
                "experiences": experiences,
                "playbooks": playbooks,
            },
            indent=2,
        )


class PersistBookingExperienceTool(BaseTool):
    """Store booking outcomes to NeoFS and beVec for future retrieval."""

    name: str = "persist_booking_experience"
    description: str = """
    Persist a booking outcome summary. Uploads raw payload to NeoFS (if provided) and
    upserts an embedding into the beVec `user_experiences` collection.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Short summary of the experience"},
            "metadata": {"type": "object", "description": "Metadata tags (location, cuisine, job_id, rating, etc.)"},
            "raw_payload": {"type": "object", "description": "Optional full result document"},
        },
        "required": ["summary", "metadata"],
    }

    def __init__(self, vector_client: Optional[BeVecClient]):
        super().__init__()
        self._vector_client = vector_client

    async def execute(self, summary: str, metadata: dict, raw_payload: dict | None = None) -> str:
        if not self._vector_client:
            return json.dumps({"success": False, "error": "beVec not configured"})

        neofs_uri = None
        if raw_payload:
            try:
                client = get_neofs_client()
                result = await client.upload_json(raw_payload, filename="booking-result.json")
                neofs_uri = f"neofs://{result.container_id}/{result.object_id}"
            except Exception as e:
                neofs_uri = None
                # Continue even if NeoFS write fails

        try:
            vector = await embed_text(summary)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Embedding failed: {e}"})

        record_id_source = metadata.get("job_id") or metadata.get("user_id") or summary
        record_id = hashlib.sha256(str(record_id_source).encode("utf-8")).hexdigest()

        enriched_metadata = {**metadata}
        if neofs_uri:
            enriched_metadata["source_uri"] = neofs_uri

        try:
            await self._vector_client.upsert(
                collection="user_experiences",
                records=[VectorRecord(id=record_id, vector=vector, metadata=enriched_metadata)],
            )
        except Exception as e:
            return json.dumps({"success": False, "error": f"beVec upsert failed: {e}"})

        return json.dumps(
            {
                "success": True,
                "record_id": record_id,
                "source_uri": neofs_uri,
            },
            indent=2,
        )


# ==============================================================================
# BID MANAGEMENT TOOLS
# ==============================================================================


class PostJobTool(BaseTool):
    """Post a job to the OrderBook contract."""

    name: str = "post_job"
    description: str = """
    Post a job to the OrderBook smart contract. Budget should be in USDC micro-units
    (1 USDC = 1_000_000). If you only have a float budget_usdc, provide that instead
    and it will be converted.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Job description"},
            "job_type": {"type": "integer", "description": "JobType enum id", "default": JobType.COMPOSITE.value},
            "budget": {"type": "integer", "description": "Budget in micro USDC", "default": 0},
            "budget_usdc": {"type": "number", "description": "Budget in USDC (will be converted)", "default": 0},
            "deadline": {"type": "integer", "description": "Deadline in seconds", "default": 0},
        },
        "required": ["description"],
    }

    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet

    async def execute(
        self,
        description: str,
        job_type: int = JobType.COMPOSITE.value,
        budget: int = 0,
        budget_usdc: float = 0,
        deadline: int = 0,
    ) -> str:
        if not self._wallet:
            return json.dumps({"success": False, "error": "Wallet not configured"})

        try:
            contracts = get_contracts(self._wallet.private_key)
        except Exception as e:
            return json.dumps({"success": False, "error": f"Contract setup failed: {e}"})

        resolved_budget = budget or int(budget_usdc * 1_000_000)
        try:
            job_id = post_job(contracts, description, job_type, resolved_budget, deadline)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

        return json.dumps({
            "success": True,
            "job_id": job_id,
            "job_type": job_type,
            "budget": resolved_budget,
            "deadline": deadline,
        }, indent=2)

class GetBidsForJobTool(BaseTool):
    """
    Get all bids for a specific job.
    """
    name: str = "get_bids_for_job"
    description: str = """
    Retrieve all bids submitted by worker agents for a specific job.
    Returns bid details including bidder address, amount, estimated time, and metadata.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID to get bids for"
            }
        },
        "required": ["job_id"]
    }
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(self, job_id: int) -> str:
        """Get bids for a job from the OrderBook contract"""
        try:
            from ..shared.contracts import get_contracts, get_bids_for_job
            
            contracts = get_contracts(self._wallet.private_key)
            bids = get_bids_for_job(contracts, job_id)
            
            formatted_bids = []
            for bid in bids:
                bid_id, bidder, amount, estimated_time, metadata_uri = bid[:5]
                formatted_bids.append({
                    "bid_id": bid_id,
                    "bidder": bidder,
                    "amount_usdc": amount / 1_000_000,  # Convert from micro-units
                    "estimated_time_hours": estimated_time / 3600,
                    "metadata_uri": metadata_uri
                })
            
            return json.dumps({
                "success": True,
                "job_id": job_id,
                "bids": formatted_bids,
                "total_bids": len(formatted_bids)
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class SelectBestBidTool(BaseTool):
    """
    Analyze bids and select the best worker.
    """
    name: str = "select_best_bid"
    description: str = """
    Analyze available bids for a job and recommend the best worker based on:
    - Bid amount (cost efficiency)
    - Estimated completion time
    - Worker reputation (if available)
    
    Returns the recommended bid with reasoning.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            },
            "bids": {
                "type": "array",
                "description": "List of bids to analyze (from get_bids_for_job)",
                "items": {"type": "object"}
            },
            "priority": {
                "type": "string",
                "enum": ["cost", "speed", "balanced"],
                "description": "Selection priority (default: balanced)"
            }
        },
        "required": ["job_id", "bids"]
    }
    
    async def execute(
        self, 
        job_id: int, 
        bids: list,
        priority: str = "balanced"
    ) -> str:
        """Analyze and select the best bid"""
        if not bids:
            return json.dumps({
                "success": False,
                "error": "No bids available for selection"
            })
        
        # Score each bid
        scored_bids = []
        for bid in bids:
            amount = bid.get("amount_usdc", float('inf'))
            time_hours = bid.get("estimated_time_hours", float('inf'))
            
            # Calculate score based on priority
            if priority == "cost":
                score = amount  # Lower is better
            elif priority == "speed":
                score = time_hours * 1000  # Lower is better
            else:  # balanced
                score = amount + (time_hours * 10)  # Combined score
            
            scored_bids.append({
                **bid,
                "score": score
            })
        
        # Sort by score (lower is better)
        scored_bids.sort(key=lambda x: x["score"])
        best_bid = scored_bids[0]
        
        return json.dumps({
            "success": True,
            "job_id": job_id,
            "priority": priority,
            "recommended_bid": best_bid,
            "reasoning": f"Selected based on {priority} priority. Score: {best_bid['score']:.2f}",
            "alternatives": scored_bids[1:3] if len(scored_bids) > 1 else []
        }, indent=2)


class AcceptBidTool(BaseTool):
    """
    Accept a worker's bid on the blockchain.
    """
    name: str = "accept_bid"
    description: str = """
    Accept a worker's bid for a job on the OrderBook contract.
    This will:
    - Lock funds in escrow
    - Officially assign the job to the worker
    - Emit BidAccepted event
    
    Call this after selecting the best bid.
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
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(self, job_id: int, bid_id: int) -> str:
        """Accept a bid on-chain"""
        try:
            from ..shared.contracts import get_contracts, accept_bid
            
            contracts = get_contracts(self._wallet.private_key)
            
            # Accept the bid
            tx_hash = accept_bid(
                contracts,
                job_id,
                bid_id,
                f"ipfs://manager-acceptance-{job_id}-{bid_id}"
            )
            
            return json.dumps({
                "success": True,
                "transaction_hash": tx_hash,
                "job_id": job_id,
                "bid_id": bid_id,
                "status": "Bid accepted, funds locked in escrow"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


# ==============================================================================
# WORKER COORDINATION TOOLS
# ==============================================================================

class SendA2AMessageTool(BaseTool):
    """
    Send A2A message to a worker agent.
    """
    name: str = "send_a2a_message"
    description: str = """
    Send a signed Agent-to-Agent (A2A) message to a worker agent.
    Use this to:
    - Request task execution
    - Query worker status
    - Send task parameters
    
    The message is signed with the manager's private key for authentication.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "agent_type": {
                "type": "string",
                "enum": ["scraper", "caller"],
                "description": "Type of worker agent to message"
            },
            "method": {
                "type": "string",
                "description": "A2A method (e.g., 'tasks/execute', 'ping', 'capabilities')"
            },
            "params": {
                "type": "object",
                "description": "Message parameters"
            }
        },
        "required": ["agent_type", "method"]
    }
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(
        self,
        agent_type: str,
        method: str,
        params: dict = None
    ) -> str:
        """Send A2A message to worker agent"""
        try:
            from eth_account import Account
            
            # Get worker endpoint
            endpoints = get_agent_endpoints()
            endpoint = getattr(endpoints, agent_type, None)
            
            if not endpoint:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown agent type: {agent_type}"
                })
            
            account = Account.from_key(self._wallet.private_key)
            
            # Build and sign message
            message = A2AMessage(
                id=1,
                method=method,
                params=params or {}
            )
            signed_message = sign_message(message, account)
            
            # Send to worker
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{endpoint}/v1/rpc",
                    json=signed_message.model_dump()
                )
                response.raise_for_status()
                result = response.json()
            
            return json.dumps({
                "success": True,
                "agent": agent_type,
                "method": method,
                "response": result
            }, indent=2)
            
        except httpx.HTTPError as e:
            return json.dumps({
                "success": False,
                "error": f"HTTP error: {str(e)}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class RequestTaskExecutionTool(BaseTool):
    """
    Request a worker agent to execute a task.
    """
    name: str = "request_task_execution"
    description: str = """
    Send a task execution request to a worker agent.
    This is used after a bid is accepted to initiate the actual work.
    
    Provide the job details and task parameters for the worker.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "agent_type": {
                "type": "string",
                "enum": ["scraper", "caller"],
                "description": "Type of worker agent"
            },
            "job_id": {
                "type": "integer",
                "description": "The job ID"
            },
            "task_type": {
                "type": "string",
                "description": "Task type (TIKTOK_SCRAPE, WEB_SCRAPE, CALL_VERIFICATION)"
            },
            "task_description": {
                "type": "string",
                "description": "What the worker should do"
            },
            "parameters": {
                "type": "object",
                "description": "Task-specific parameters"
            }
        },
        "required": ["agent_type", "job_id", "task_type", "task_description"]
    }
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(
        self,
        agent_type: str,
        job_id: int,
        task_type: str,
        task_description: str,
        parameters: dict = None
    ) -> str:
        """Request task execution from worker"""
        try:
            from eth_account import Account
            
            endpoints = get_agent_endpoints()
            endpoint = getattr(endpoints, agent_type, None)
            
            if not endpoint:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown agent type: {agent_type}"
                })
            
            account = Account.from_key(self._wallet.private_key)
            
            # Build execution request
            message = A2AMessage(
                id=job_id,
                method=A2AMethod.EXECUTE_TASK.value,
                params={
                    "job_id": job_id,
                    "task_type": task_type,
                    "description": task_description,
                    "parameters": parameters or {},
                    "deadline": 3600  # 1 hour deadline
                }
            )
            signed_message = sign_message(message, account)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{endpoint}/v1/rpc",
                    json=signed_message.model_dump()
                )
                response.raise_for_status()
                result = response.json()
            
            return json.dumps({
                "success": True,
                "job_id": job_id,
                "agent": agent_type,
                "task_type": task_type,
                "response": result,
                "status": "Task execution requested"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


# ==============================================================================
# JOB FINALIZATION TOOLS
# ==============================================================================

class ApproveDeliveryTool(BaseTool):
    """
    Approve a delivery and release payment.
    """
    name: str = "approve_delivery"
    description: str = """
    Approve a worker's delivery for a job.
    This will:
    - Verify the delivery was submitted
    - Release escrowed funds to the worker
    - Update job status to completed
    
    Only call this after verifying the work is satisfactory.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "integer",
                "description": "The job ID to finalize"
            },
            "approval_notes": {
                "type": "string",
                "description": "Notes about the approval/verification"
            }
        },
        "required": ["job_id"]
    }
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(self, job_id: int, approval_notes: str = "") -> str:
        """Approve delivery and release payment"""
        try:
            from ..shared.contracts import get_contracts, approve_delivery
            
            contracts = get_contracts(self._wallet.private_key)
            tx_hash = approve_delivery(contracts, job_id)
            
            return json.dumps({
                "success": True,
                "transaction_hash": tx_hash,
                "job_id": job_id,
                "approval_notes": approval_notes,
                "status": "Delivery approved, payment released"
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class GetJobDetailsTool(BaseTool):
    """
    Get detailed information about a job.
    """
    name: str = "get_job_details"
    description: str = """
    Get comprehensive details about a job from the blockchain.
    Includes job status, assigned worker, deadline, and deliveries.
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
    
    def __init__(self, wallet: AgentWallet):
        super().__init__()
        self._wallet = wallet
    
    async def execute(self, job_id: int) -> str:
        """Get job details from blockchain"""
        try:
            from ..shared.contracts import get_contracts, get_job
            
            contracts = get_contracts(self._wallet.private_key)
            job = get_job(contracts, job_id)
            
            return json.dumps({
                "success": True,
                "job_id": job_id,
                "job": job
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class GetAgentEndpointsTool(BaseTool):
    """
    Get A2A endpoints for worker agents.
    """
    name: str = "get_agent_endpoints"
    description: str = """
    Get the A2A endpoint URLs for all worker agents.
    Use these to send A2A messages for task coordination.
    """
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    async def execute(self) -> str:
        """Get worker agent endpoints"""
        endpoints = get_agent_endpoints()
        return json.dumps({
            "scraper": endpoints.scraper,
            "caller": endpoints.caller,
            "manager": endpoints.manager
        }, indent=2)


# ==============================================================================
# TOOL FACTORY
# ==============================================================================

def get_manager_tools(wallet: AgentWallet, vector_client: Optional[BeVecClient] = None) -> list[BaseTool]:
    """
    Get all tools for the Manager Agent.
    
    Args:
        wallet: The agent's wallet for signing transactions
        
    Returns:
        List of configured tools
    """
    tools: list[BaseTool] = [
        # Booking + RAG helpers
        CollectBookingRequirementsTool(),
        BuildBookingContextTool(vector_client),
        
        # Job decomposition
        DecomposeJobTool(),
        
        # Job posting / bid management
        PostJobTool(wallet),
        GetBidsForJobTool(wallet),
        SelectBestBidTool(),
        AcceptBidTool(wallet),
        
        # Worker coordination
        SendA2AMessageTool(wallet),
        RequestTaskExecutionTool(wallet),
        
        # Job finalization
        ApproveDeliveryTool(wallet),
        GetJobDetailsTool(wallet),
        GetAgentEndpointsTool(),
    ]

    if vector_client:
        tools.append(PersistBookingExperienceTool(vector_client))

    return tools
