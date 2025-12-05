"""
Scraper Agent Tools

SpoonOS tools for:
- TikTok scraping via Bright Data
- General web scraping
- NeoFS storage
- Job-specific operations

These are the EXECUTION tools - bidding is handled by shared bidding_tools.
"""

import os
import json
import asyncio
from typing import Any, Optional
from datetime import datetime

import httpx
from pydantic import Field
from web3 import Web3

from spoon_ai.tools.base import BaseTool

from ..shared.neofs import get_neofs_client


class TikTokScrapeTool(BaseTool):
    """
    Tool to scrape TikTok content using Bright Data API.
    """
    name: str = "scrape_tiktok"
    description: str = """
    Scrape TikTok videos and posts using Bright Data's Web Scraper API.
    
    Use this to search for TikTok content and return structured data including:
    - Video URLs and thumbnails
    - Captions and hashtags
    - Engagement metrics (likes, comments, shares)
    - Creator information
    
    This is an async operation - results may take 30-60 seconds.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "search_query": {
                "type": "string",
                "description": "The search query for TikTok (e.g., 'moscow restaurants trendy')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10, max: 50)"
            },
            "location": {
                "type": "string",
                "description": "Optional location filter (e.g., 'Russia', 'Moscow')"
            }
        },
        "required": ["search_query"]
    }
    
    async def execute(
        self, 
        search_query: str, 
        max_results: int = 10,
        location: str = None
    ) -> str:
        """Scrape TikTok using Bright Data API"""
        api_token = os.getenv("BRIGHT_DATA_API_KEY")
        
        if not api_token:
            return json.dumps({
                "success": False,
                "error": "BRIGHT_DATA_API_KEY not configured"
            })
        
        max_results = min(max_results, 50)  # Cap at 50
        
        try:
            # Bright Data Web Scraper API for TikTok
            api_url = "https://api.brightdata.com/datasets/v3/trigger"
            
            # Build the TikTok search URL
            tiktok_search_url = f"https://www.tiktok.com/search?q={search_query.replace(' ', '+')}"
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Trigger the scrape
                response = await client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "dataset_id": "gd_lu702otf1h4ggj6b5h",  # TikTok posts dataset
                        "input": [{"url": tiktok_search_url}],
                        "format": "json",
                        "limit": max_results
                    }
                )
                response.raise_for_status()
                trigger_result = response.json()
                
                snapshot_id = trigger_result.get("snapshot_id")
                
                if not snapshot_id:
                    return json.dumps({
                        "success": False,
                        "error": "Failed to get snapshot ID from Bright Data"
                    })
                
                # Poll for results
                results = await self._poll_for_results(client, api_token, snapshot_id)
                
                return json.dumps({
                    "success": True,
                    "query": search_query,
                    "location": location,
                    "snapshot_id": snapshot_id,
                    "results": results,
                    "count": len(results) if results else 0
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
    
    async def _poll_for_results(
        self, 
        client: httpx.AsyncClient, 
        api_token: str, 
        snapshot_id: str,
        max_attempts: int = 20
    ) -> list:
        """Poll Bright Data for scraping results"""
        base_delay = 3
        
        for attempt in range(max_attempts):
            try:
                response = await client.get(
                    f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                    headers={"Authorization": f"Bearer {api_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ready":
                        return data.get("data", [])
                    elif data.get("status") == "failed":
                        raise Exception(f"Scrape failed: {data.get('error')}")
                
                # Exponential backoff
                delay = base_delay * (1.5 ** attempt)
                await asyncio.sleep(min(delay, 60))
                
            except httpx.HTTPError:
                await asyncio.sleep(base_delay)
        
        raise Exception("Scrape timeout - results not ready")


class WebScrapeTool(BaseTool):
    """
    Tool for general web scraping.
    """
    name: str = "web_scrape"
    description: str = """
    Scrape content from web pages.
    
    Fetches and extracts content from a given URL or search query.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to scrape"
            },
            "search_query": {
                "type": "string",
                "description": "Alternative: search query (will use search engine)"
            }
        },
        "required": []
    }
    
    async def execute(self, url: str = None, search_query: str = None) -> str:
        """Scrape web content"""
        if not url and not search_query:
            return json.dumps({
                "success": False,
                "error": "Either url or search_query is required"
            })
        
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            ) as client:
                target_url = url or f"https://www.google.com/search?q={search_query}"
                
                response = await client.get(
                    target_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()
                
                # Return raw HTML (in production, parse with BeautifulSoup)
                content = response.text
                
                return json.dumps({
                    "success": True,
                    "url": target_url,
                    "content_length": len(content),
                    "content_preview": content[:1000] if len(content) > 1000 else content
                }, indent=2)
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class UploadToNeoFSTool(BaseTool):
    """
    Tool to upload scraping results to NeoFS.
    """
    name: str = "upload_to_neofs"
    description: str = """
    Upload scraping results to NeoFS for decentralized storage.
    
    Returns the object ID which can be used as proof-of-work.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "The data to upload (JSON serializable)"
            },
            "job_id": {
                "type": "integer",
                "description": "The job ID this result belongs to"
            },
            "source": {
                "type": "string",
                "description": "Source identifier (e.g., 'tiktok', 'web')"
            }
        },
        "required": ["data", "job_id", "source"]
    }
    
    async def execute(self, data: dict, job_id: int, source: str) -> str:
        """Upload data to NeoFS"""
        try:
            neofs = get_neofs_client()
            
            result = await neofs.upload_scraping_results(
                data,
                str(job_id),
                source
            )
            
            await neofs.close()
            
            return json.dumps({
                "success": True,
                "object_id": result.object_id,
                "container_id": result.container_id,
                "job_id": job_id,
                "source": source
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class ComputeProofHashTool(BaseTool):
    """
    Tool to compute proof hash from NeoFS object ID.
    """
    name: str = "compute_proof_hash"
    description: str = """
    Compute a proof hash from a NeoFS object ID for delivery submission.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "neofs_object_id": {
                "type": "string",
                "description": "The NeoFS object ID"
            }
        },
        "required": ["neofs_object_id"]
    }
    
    async def execute(self, neofs_object_id: str) -> str:
        """Compute proof hash"""
        try:
            proof_hash = Web3.keccak(text=neofs_object_id)
            
            return json.dumps({
                "success": True,
                "neofs_object_id": neofs_object_id,
                "proof_hash": proof_hash.hex()
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


def create_scraper_tools() -> list[BaseTool]:
    """
    Create all scraper-specific tools.
    
    Note: Bidding and wallet tools are created separately in the agent.
    """
    return [
        TikTokScrapeTool(),
        WebScrapeTool(),
        UploadToNeoFSTool(),
        ComputeProofHashTool(),
    ]

