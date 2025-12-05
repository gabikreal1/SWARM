"""
beVec Vector DB client helpers.

This wrapper keeps our usage narrow: upsert vectors with metadata and query by vector
with optional tag filters. Adjust endpoints/payloads if your beVec deployment uses a
different API shape.
"""

import os
import json
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import httpx


@dataclass
class VectorRecord:
    """Vector payload for upsert operations."""
    id: str
    vector: Sequence[float]
    metadata: dict
    namespace: Optional[str] = None


@dataclass
class QueryResult:
    id: str
    score: float
    metadata: dict
    namespace: Optional[str] = None


class BeVecClient:
    """Minimal async client for beVec."""

    def __init__(self, endpoint: str, api_key: str | None = None, namespace: str | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.namespace = namespace
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(timeout=20.0, headers=headers)

    async def close(self):
        await self.client.aclose()

    async def upsert(self, collection: str, records: list[VectorRecord]) -> dict:
        """Upsert vectors into a collection."""
        payload = {
            "points": [
                {
                    "id": r.id,
                    "vector": r.vector,
                    "metadata": r.metadata,
                    "namespace": r.namespace or self.namespace,
                }
                for r in records
            ]
        }

        response = await self.client.post(f"{self.endpoint}/v1/collections/{collection}/points", json=payload)
        response.raise_for_status()
        return response.json()

    async def query(
        self,
        collection: str,
        vector: Sequence[float],
        top_k: int = 5,
        tags: list[str] | None = None,
        metadata_filter: dict | None = None,
    ) -> list[QueryResult]:
        """Query nearest neighbors with optional tag/metadata filters."""
        payload: dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
        }

        # Simple filter model: match any tag in metadata.tags and exact matches in metadata_filter
        filters = []
        if tags:
            filters.append({"key": "tags", "operator": "contains_any", "value": tags})
        if metadata_filter:
            for key, value in metadata_filter.items():
                filters.append({"key": key, "operator": "eq", "value": value})
        if filters:
            payload["filter"] = filters

        response = await self.client.post(f"{self.endpoint}/v1/collections/{collection}/query", json=payload)
        response.raise_for_status()
        data = response.json()

        matches = data.get("matches") or data.get("points") or []
        results: list[QueryResult] = []
        for item in matches:
            results.append(
                QueryResult(
                    id=item.get("id", ""),
                    score=item.get("score") or item.get("similarity", 0.0),
                    metadata=item.get("metadata", {}),
                    namespace=item.get("namespace"),
                )
            )
        return results


def create_bevec_client() -> Optional[BeVecClient]:
    """Instantiate a beVec client from environment variables."""
    endpoint = os.getenv("BEVEC_ENDPOINT")
    api_key = os.getenv("BEVEC_API_KEY")
    namespace = os.getenv("BEVEC_NAMESPACE")
    if not endpoint:
        return None
    return BeVecClient(endpoint=endpoint, api_key=api_key, namespace=namespace)

