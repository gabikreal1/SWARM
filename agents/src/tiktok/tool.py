"""
TikTok Search Tool

Wraps the scraper TikTok tool into a single callable SpoonOS tool that
returns the top hit plus the full result list.
"""
import json
from typing import Optional

from spoon_ai.tools.base import BaseTool
from agents.src.scraper.tools import TikTokScrapeTool


class TikTokSearchTool(BaseTool):
    name: str = "tiktok_search"
    description: str = (
        "Search TikTok for videos matching a query and return structured results "
        "(video URL, caption, creator, engagement). Requires BRIGHT_DATA_API_KEY."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search text to find relevant TikTok videos.",
            },
            "max_results": {
                "type": "integer",
                "description": "How many results to return (default 5, max 50).",
            },
            "location": {
                "type": "string",
                "description": "Optional location filter such as 'USA' or 'Moscow'.",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self, query: str, max_results: int = 5, location: Optional[str] = None
    ) -> str:
        tool = TikTokScrapeTool()
        raw = await tool.execute(
            search_query=query, max_results=max_results, location=location
        )
        data = json.loads(raw)
        if not data.get("success"):
            return json.dumps(
                {"success": False, "error": data.get("error", "Scrape failed")}
            )

        results = data.get("results", []) or []
        top_result = results[0] if results else None

        return json.dumps(
            {
                "success": True,
                "query": query,
                "count": data.get("count", len(results)),
                "top_result": top_result,
                "results": results,
                "snapshot_id": data.get("snapshot_id"),
            }
        )


def create_tiktok_tools() -> list[BaseTool]:
    """Factory to provide all TikTok tools for SpoonOS agents."""
    return [TikTokSearchTool(), TikTokScrapeTool()]
