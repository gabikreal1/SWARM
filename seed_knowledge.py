"""
Seed sample knowledge for restaurant booking into Qdrant and Mem0.

Requires env vars:
- OPENAI_API_KEY
- QDRANT_URL
- QDRANT_API_KEY
- MEM0_API_KEY
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mem0 import MemoryClient  # type: ignore
from openai import OpenAI  # type: ignore
from qdrant_client import QdrantClient  # type: ignore
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, VectorParams  # type: ignore


OPENAI_MODEL = "text-embedding-3-small"
QDRANT_COLLECTION = "butler_restaurant_kb"
MEM0_COLLECTION_USER = "butler_restaurant_kb"
MEM0_COLLECTION_GLOBAL = "butler_restaurant_kb_global"


@dataclass
class SeedItem:
    title: str
    content: str
    tags: List[str]
    category: str

    def as_text(self) -> str:
        return json.dumps(
            {
                "title": self.title,
                "content": self.content,
                "tags": self.tags,
                "category": self.category,
            },
            ensure_ascii=True,
        )


def load_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing env var: {key}")
    return val


def embed_text(client: OpenAI, text: str) -> List[float]:
    resp = client.embeddings.create(model=OPENAI_MODEL, input=text)
    return list(resp.data[0].embedding)


def ensure_qdrant_collection(client: QdrantClient, dim: int) -> None:
    if client.collection_exists(QDRANT_COLLECTION):
        try:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION,
                field_name="privacy",
                field_schema="keyword",
            )
        except Exception:
            pass
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )
    try:
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name="privacy",
            field_schema="keyword",
        )
    except Exception:
        pass


def seed_qdrant(
    client: QdrantClient, items: List[SeedItem], vectors: List[List[float]]
) -> None:
    points = []
    for idx, (item, vec) in enumerate(zip(items, vectors)):
        points.append(
            {
                "id": idx + 1,
                "vector": vec,
                "payload": {
                    "title": item.title,
                    "content": item.content,
                    "tags": item.tags,
                    "category": item.category,
                    "privacy": "anonymized",
                },
            }
        )
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def seed_mem0(mem: MemoryClient, items: List[SeedItem]) -> None:
    # Per-user memory is optional; we seed global/anonymized here with a required filter.
    for item in items:
        mem.add(
            item.as_text(),
            collection=MEM0_COLLECTION_GLOBAL,
            metadata={"privacy": "anonymized", "category": item.category},
            filters={"user_id": "anon_global"},
            user_id="anon_global",
        )


def search_qdrant(client: QdrantClient, query_vec: List[float]) -> Any:
    flt = Filter(
        must=[FieldCondition(key="privacy", match=MatchValue(value="anonymized"))]
    )
    try:
        return client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vec,
            limit=3,
            query_filter=flt,
        )
    except AttributeError:
        # Fallback for clients exposing query_points instead of search
        return client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vec,
            limit=3,
            query_filter=flt,
        )


def main() -> None:
    # Seed data
    items = [
        SeedItem(
            title="Booking workflow",
            content="Gather party size, date, time, cuisine preference, budget, and location. Confirm dietary restrictions. Propose 2-3 options and hold a table.",
            tags=["workflow", "booking"],
            category="process",
        ),
        SeedItem(
            title="Cancellation policy",
            content="If reservation requires card hold, inform user about no-show fee. Cancel at least 2 hours prior to avoid charges.",
            tags=["policy", "fees"],
            category="policy",
        ),
        SeedItem(
            title="Dietary handling",
            content="Ask for allergies (nuts, shellfish, gluten) and dietary preferences (vegan, halal, kosher). Communicate these when booking.",
            tags=["allergies", "diet"],
            category="safety",
        ),
        SeedItem(
            title="Follow-up template",
            content="“I’ve secured a table for {party_size} at {restaurant} on {date} at {time}. Preferences noted: {notes}. Do you want me to share directions?”",
            tags=["template", "messaging"],
            category="templates",
        ),
        SeedItem(
            title="Peak hours guidance",
            content="For popular spots, target off-peak times (before 6pm or after 8:30pm) to improve availability. Offer nearby alternatives if prime slots are full.",
            tags=["availability", "timing"],
            category="tips",
        ),
        SeedItem(
            title="Group seating",
            content="For parties >6, ask if split tables are acceptable. Check if restaurant requires prefix menu or deposit for large groups.",
            tags=["groups", "seating"],
            category="policy",
        ),
        SeedItem(
            title="Special occasions",
            content="If birthday/anniversary, ask about dessert message, candle, or quiet corner. Note occasion in booking and request a nice table if possible.",
            tags=["occasion", "experience"],
            category="service",
        ),
        SeedItem(
            title="Accessibility",
            content="Ask if step-free access or wheelchair seating is needed. Request accessible table/entrance info from the venue.",
            tags=["accessibility", "safety"],
            category="safety",
        ),
        SeedItem(
            title="Kid-friendly options",
            content="If children attending, check for high chair, kids menu, and quiet seating. Avoid late slots and very formal venues.",
            tags=["family", "kids"],
            category="experience",
        ),
        SeedItem(
            title="Cuisine preferences",
            content="Clarify cuisine type (Italian, Japanese, Mediterranean), spice tolerance, and whether tasting menu is acceptable.",
            tags=["cuisine", "preferences"],
            category="discovery",
        ),
        SeedItem(
            title="Budget bands",
            content="Capture budget per person (low <$30, mid $30-60, high $60-120, premium $120+). Filter options accordingly before proposing.",
            tags=["budget", "filtering"],
            category="discovery",
        ),
        SeedItem(
            title="Confirmation checklist",
            content="Before confirming: date/time, party size, name, phone/email, dietary notes, occasion, payment hold, cancellation terms.",
            tags=["checklist", "confirmation"],
            category="process",
        ),
        SeedItem(
            title="Post-booking support",
            content="After confirmation, offer directions, parking info, dress code, and remind about cancellation window.",
            tags=["followup", "concierge"],
            category="service",
        ),
    ]

    # Clients
    openai_client = OpenAI(api_key=load_env("OPENAI_API_KEY"))
    qdrant_client = QdrantClient(
        url=load_env("QDRANT_URL"),
        api_key=load_env("QDRANT_API_KEY"),
    )
    mem0_client = MemoryClient(api_key=load_env("MEM0_API_KEY"))

    # Embeddings
    vectors = [embed_text(openai_client, item.as_text()) for item in items]
    ensure_qdrant_collection(qdrant_client, len(vectors[0]))
    seed_qdrant(qdrant_client, items, vectors)

    # Mem0
    seed_mem0(mem0_client, items)

    # Quick sanity search
    query_vec = embed_text(openai_client, "allergy and dietary guidance")
    results = search_qdrant(qdrant_client, query_vec)
    print("Qdrant sample search (top 3):")
    for hit in results:
        payload = getattr(hit, "payload", {}) or {}
        print("-", payload.get("title"), "| score:", getattr(hit, "score", None))

    print("Mem0 seeded", len(items), "items to collection", MEM0_COLLECTION_GLOBAL)


if __name__ == "__main__":
    main()
