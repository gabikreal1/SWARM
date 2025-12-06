"""
Minimal slot/questioning helper for SpoonOS agents.

Features:
- Defines a simple InputSlot schema and SlotFiller that suggests missing slots and clarifying questions.
- Uses SpoonMem0 long-term memory when available (per-user first, anonymized global fallback).
- Ranks missing slots with similarity-weighted voting and tool-required parameter priority.
- Provides a CLI-style demo at the bottom.
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Optional memory support
try:
    from spoon_ai.memory.mem0_client import SpoonMem0
except ImportError:
    SpoonMem0 = None

logger = logging.getLogger(__name__)


# ----------------------------
# Data models
# ----------------------------


@dataclass(frozen=True)
class InputSlot:
    """Simple slot schema."""

    name: str
    description: str = ""
    question_template: str = "Could you provide your {slot}?"

    def make_question(self) -> str:
        return self.question_template.format(slot=self.name.replace("_", " "))


@dataclass
class TemplateRecord:
    """Stored template for few-shot style recall."""

    task_summary: str
    final_slots: Dict[str, Any]
    questions_asked: List[str]
    chosen_tool: str
    success: bool
    similarity: float = 1.0  # Mem0 wrapper doesn't expose score; default to 1.0.
    privacy: Optional[str] = None

    def to_text(self) -> str:
        payload = {
            "task_summary": self.task_summary,
            "final_slots": self.final_slots,
            "questions_asked": self.questions_asked,
            "chosen_tool": self.chosen_tool,
            "success": self.success,
            "privacy": self.privacy,
        }
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def from_text(blob: str, similarity: float = 1.0) -> Optional["TemplateRecord"]:
        try:
            data = json.loads(blob)
            return TemplateRecord(
                task_summary=str(data.get("task_summary", "")),
                final_slots=dict(data.get("final_slots") or {}),
                questions_asked=list(data.get("questions_asked") or []),
                chosen_tool=str(data.get("chosen_tool", "")),
                success=bool(data.get("success", False)),
                similarity=similarity,
                privacy=data.get("privacy"),
            )
        except Exception:
            logger.debug("Failed to parse stored template text: %s", blob)
            return None

    def build_query_text(self) -> str:
        """Combine fields for embedding-based similarity."""
        final_slots = {k: ("<filled>" if v else "<missing>") for k, v in self.final_slots.items()}
        return (
            f"summary: {self.task_summary}\n"
            f"tool: {self.chosen_tool}\n"
            f"slots: {json.dumps(final_slots, ensure_ascii=True)}"
        )

# ----------------------------
# Memory helpers
# ----------------------------


class TemplateMemory:
    """Handles storing and retrieving templates with per-user preference and global fallback."""

    def __init__(
        self,
        user_id: Optional[str],
        per_user_collection: str = "templates",
        global_collection: str = "global_templates",
    ) -> None:
        self.user_id = user_id
        if SpoonMem0 is not None:
            self.user_mem = SpoonMem0(
                {
                    "user_id": user_id,
                    "collection": per_user_collection,
                    "filters": {"user_id": user_id} if user_id else {},
                }
            )
            self.global_mem = SpoonMem0(
                {
                    "collection": global_collection,
                    "metadata": {"privacy": "anonymized"},
                    # Mem0 requires at least one filter; use an agent_id marker plus anonymized user_id.
                    "user_id": "anon_global",
                    "filters": {"agent_id": "global_templates", "user_id": "anon_global"},
                }
            )
        else:
            self.user_mem = None
            self.global_mem = None

    def search(self, query: str, min_hits: int = 2) -> List[TemplateRecord]:
        """Search per-user first, then global anonymized fallback."""
        hits: List[TemplateRecord] = []

        # Per-user
        if self.user_mem and self.user_mem.is_ready():
            hits = self._parse_results(self.user_mem.search_memory(query))

        # Global fallback if not enough
        if len(hits) < min_hits and self.global_mem and self.global_mem.is_ready():
            global_hits = self._parse_results(self.global_mem.search_memory(query))
            # Tag privacy on global hits
            for h in global_hits:
                h.privacy = h.privacy or "anonymized"
            hits.extend(global_hits)

        return hits

    def store(self, record: TemplateRecord) -> None:
        """Store per-user (if available) and anonymized global copy."""
        if self.user_mem and self.user_mem.is_ready():
            try:
                self.user_mem.add_text(record.to_text(), user_id=self.user_id)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Per-user template store failed: %s", exc)

        if self.global_mem and self.global_mem.is_ready():
            global_copy = TemplateRecord(
                task_summary=record.task_summary,
                final_slots=record.final_slots,
                questions_asked=record.questions_asked,
                chosen_tool=record.chosen_tool,
                success=record.success,
                similarity=record.similarity,
                privacy="anonymized",
            )
            try:
                self.global_mem.add_text(
                    global_copy.to_text(),
                    metadata={"privacy": "anonymized"},
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Global template store failed: %s", exc)

    @staticmethod
    def _parse_results(results: Iterable[str]) -> List[TemplateRecord]:
        parsed: List[TemplateRecord] = []
        for raw in results or []:
            rec = TemplateRecord.from_text(raw)
            if rec:
                parsed.append(rec)
        return parsed


# ----------------------------
# Embedding helpers
# ----------------------------


class EmbeddingModel:
    """Embedding provider with OpenAI (if available) and a deterministic fallback."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self.openai_client = self._try_openai()
        self.fallback_dim = 128

    def _try_openai(self):
        try:
            import openai  # type: ignore

            return openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception:
            return None

    def embed(self, text: str) -> List[float]:
        if not text:
            return []
        if self.openai_client:
            try:
                resp = self.openai_client.embeddings.create(model=self.model, input=text)
                return list(resp.data[0].embedding)
            except Exception as exc:  # pragma: no cover - external call
                logger.debug("OpenAI embedding failed, falling back: %s", exc)
        return self._hash_embed(text)

    @staticmethod
    def _hash_embed(text: str, dim: int = 128) -> List[float]:
        """Deterministic lightweight embedding using hashing (fallback)."""
        vec = [0.0] * dim
        for token in text.lower().split():
            h = hash(token)
            idx = h % dim
            vec[idx] += 1.0
        return vec

    @staticmethod
    def cosine(a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b:
            return 0.0
        length = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(length))
        na = math.sqrt(sum(a[i] * a[i] for i in range(length)))
        nb = math.sqrt(sum(b[i] * b[i] for i in range(length)))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


# ----------------------------
# Qdrant helpers
# ----------------------------


class QdrantTemplateStore:
    """Lightweight vector store for templates using Qdrant."""

    def __init__(
        self,
        embedder: EmbeddingModel,
        collection: str = "slot_templates",
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        upsert_global: bool = True,
    ) -> None:
        self.embedder = embedder
        self.collection = collection
        self.upsert_global = upsert_global
        self.client = self._init_client(url, api_key)
        if self.client:
            self._ensure_collection()

    def _init_client(self, url: Optional[str], api_key: Optional[str]):
        try:
            from qdrant_client import QdrantClient  # type: ignore

            return QdrantClient(url=url or os.getenv("QDRANT_URL"), api_key=api_key or os.getenv("QDRANT_API_KEY"))
        except Exception as exc:
            logger.debug("Qdrant client init failed: %s", exc)
            return None

    def is_ready(self) -> bool:
        return self.client is not None

    def _ensure_collection(self) -> None:
        if not self.client:
            return
        try:
            from qdrant_client.models import Distance, VectorParams  # type: ignore

            test_vec = self.embedder.embed("init")
            dim = len(test_vec) or self.embedder.fallback_dim
            if not self.client.collection_exists(self.collection):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
        except Exception as exc:
            logger.debug("Qdrant ensure collection failed: %s", exc)

    def upsert(self, record: TemplateRecord, user_id: Optional[str]) -> None:
        if not self.client:
            return
        from uuid import uuid4

        vector = self.embedder.embed(record.build_query_text())

        points: List[Dict[str, Any]] = []
        # Per-user copy
        points.append(
            {
                "id": str(uuid4()),
                "vector": vector,
                "payload": {
                    "blob": record.to_text(),
                    "user_id": user_id,
                    "chosen_tool": record.chosen_tool,
                    "privacy": record.privacy or "user",
                },
            }
        )
        # Optional anonymized/global copy
        if self.upsert_global:
            points.append(
                {
                    "id": str(uuid4()),
                    "vector": vector,
                    "payload": {
                        "blob": record.to_text(),
                        "user_id": "anon_global",
                        "chosen_tool": record.chosen_tool,
                        "privacy": "anonymized",
                    },
                }
            )

        try:
            self.client.upsert(collection_name=self.collection, points=points)
        except Exception as exc:
            logger.debug("Qdrant upsert failed: %s", exc)

    def search(self, query: str, limit: int = 5, user_id: Optional[str] = None) -> List[TemplateRecord]:
        if not self.client:
            return []
        vector = self.embedder.embed(query)
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore
        except Exception:
            return []

        must = []
        should = []
        if user_id:
            should.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
            should.append(FieldCondition(key="privacy", match=MatchValue(value="anonymized")))
        else:
            must.append(FieldCondition(key="privacy", match=MatchValue(value="anonymized")))

        query_filter = Filter(must=must or None, should=should or None)

        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=limit,
                query_filter=query_filter,
            )
        except Exception as exc:
            logger.debug("Qdrant search failed: %s", exc)
            return []

        parsed: List[TemplateRecord] = []
        for hit in results or []:
            payload = getattr(hit, "payload", {}) or {}
            blob = payload.get("blob")
            score = getattr(hit, "score", None)
            rec = TemplateRecord.from_text(blob, similarity=score if score is not None else 1.0) if blob else None
            if rec:
                parsed.append(rec)
        return parsed


# ----------------------------
# Slot filling core
# ----------------------------


class SlotFiller:
    """Determines missing slots and clarifying questions using tools + memory."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        max_questions: int = 3,
        min_memory_hits: int = 2,
    ) -> None:
        self.user_id = user_id
        self.max_questions = max_questions
        self.min_memory_hits = min_memory_hits
        self.memory = TemplateMemory(user_id=user_id)
        self.embedder = EmbeddingModel()
        self.qdrant_store = QdrantTemplateStore(self.embedder)

    def fill(
        self,
        user_message: str,
        current_slots: Dict[str, Any],
        candidate_tools: Sequence[Dict[str, Any]],
        chosen_tool: Optional[str] = None,
    ) -> Tuple[List[str], List[str], str]:
        """
        Returns (missing_slots_ranked, questions, chosen_tool_name).
        """
        chosen_tool_name = self._choose_tool(candidate_tools, chosen_tool)
        required_slots = self._collect_required_slots(user_message, candidate_tools, chosen_tool_name)
        missing_slots = self._rank_missing_slots(required_slots, current_slots, chosen_tool_name)
        questions = [InputSlot(name=s).make_question() for s in missing_slots[: self.max_questions]]
        return missing_slots, questions, chosen_tool_name

    def store_success(
        self,
        task_summary: str,
        final_slots: Dict[str, Any],
        questions_asked: List[str],
        chosen_tool: str,
        success: bool = True,
    ) -> None:
        """Persist a completed template to memory."""
        record = TemplateRecord(
            task_summary=task_summary,
            final_slots=final_slots,
            questions_asked=questions_asked,
            chosen_tool=chosen_tool,
            success=success,
        )
        try:
            self.memory.store(record)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Storing success template failed: %s", exc)
        if self.qdrant_store.is_ready():
            try:
                self.qdrant_store.upsert(record, user_id=self.user_id)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Qdrant store failed: %s", exc)

    # Internal helpers

    def _choose_tool(
        self, candidate_tools: Sequence[Dict[str, Any]], chosen_tool: Optional[str]
    ) -> str:
        if chosen_tool:
            return chosen_tool
        if candidate_tools:
            return str(candidate_tools[0].get("name", "unknown_tool"))
        return "unknown_tool"

    def _collect_required_slots(
        self,
        user_message: str,
        candidate_tools: Sequence[Dict[str, Any]],
        chosen_tool: str,
    ) -> Dict[str, float]:
        """
        Aggregate required slots from the chosen tool and memory-derived templates.
        Returns a mapping of slot -> base weight.
        """
        required: Dict[str, float] = {}

        # Tool-required slots (highest base weight)
        for tool in candidate_tools:
            if str(tool.get("name")) != chosen_tool:
                continue
            for param in tool.get("required_params", []):
                required[str(param)] = max(required.get(str(param), 0.0), 1.0)

        # Memory-derived slots
        templates = self.memory.search(user_message, min_hits=self.min_memory_hits)
        if self.qdrant_store.is_ready():
            templates.extend(self.qdrant_store.search(user_message, limit=5, user_id=self.user_id))

        if templates:
            slot_scores = self._score_from_templates(templates, user_message)
            for slot, score in slot_scores.items():
                required[slot] = max(required.get(slot, 0.0), score)

        return required

    def _score_from_templates(
        self, templates: Sequence[TemplateRecord], query: str
    ) -> Dict[str, float]:
        query_emb = self.embedder.embed(query)
        scores: Dict[str, float] = {}
        total_sim: Dict[str, float] = {}

        for tmpl in templates:
            # Prefer provided similarity; otherwise compute embedding similarity.
            sim = float(tmpl.similarity or 0.0)
            if sim <= 0:
                tmpl_emb = self.embedder.embed(tmpl.build_query_text())
                sim = self.embedder.cosine(query_emb, tmpl_emb)
            sim = max(sim, 0.0001)
            for slot in tmpl.final_slots.keys():
                scores[slot] = scores.get(slot, 0.0) + sim
                total_sim[slot] = total_sim.get(slot, 0.0) + sim

        ranked: Dict[str, float] = {}
        for slot, accum in scores.items():
            denom = total_sim.get(slot, 1.0)
            ranked[slot] = accum / denom if denom else 0.0
        return ranked

    def _rank_missing_slots(
        self, required_slots: Dict[str, float], current_slots: Dict[str, Any], chosen_tool: str
    ) -> List[str]:
        """Rank missing slots with tool-required slots first, then by memory score."""
        missing: List[Tuple[str, float, bool]] = []

        for slot, score in required_slots.items():
            value = current_slots.get(slot)
            if value not in (None, "", False):
                continue
            # Tool-required slots get a bump
            tool_required = score >= 0.999
            adjusted_score = score + (2.0 if tool_required else 0.0)
            missing.append((slot, adjusted_score, tool_required))

        # Sort: tool-required first, then by score desc, then name
        missing.sort(key=lambda item: (-item[2], -item[1], item[0]))
        return [slot for slot, _, _ in missing]


# ----------------------------
# CLI-style demo
# ----------------------------


def _demo() -> None:
    """Run a minimal demo in CLI style."""
    candidate_tools = [
        {"name": "book_flight", "required_params": ["origin", "destination", "date"]},
        {"name": "check_weather", "required_params": ["location", "date"]},
    ]
    user_message = "I need to book a trip to Paris next month."
    current_slots = {"destination": "Paris"}  # already known

    filler = SlotFiller(user_id="demo_user")

    # Health check
    print("Backends:")
    print("- Mem0 ready:", filler.memory.user_mem.is_ready())
    print("- Qdrant ready:", filler.qdrant_store.is_ready())
    print("- OpenAI embeddings:", bool(filler.embedder.openai_client))
    missing_slots, questions, chosen_tool = filler.fill(
        user_message=user_message,
        current_slots=current_slots,
        candidate_tools=candidate_tools,
        chosen_tool="book_flight",
    )

    print("Chosen tool:", chosen_tool)
    print("Missing slots (ranked):", missing_slots)
    print("Questions to ask:")
    for q in questions:
        print("-", q)

    # Simulate success and store a template
    final_slots = {**current_slots, "origin": "NYC", "date": "2025-12-15"}
    filler.store_success(
        task_summary="Booked a flight to Paris next month.",
        final_slots=final_slots,
        questions_asked=questions,
        chosen_tool=chosen_tool,
        success=True,
    )


if __name__ == "__main__":
    _demo()
