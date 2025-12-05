"""
Booking helper utilities for restaurant-style requests.

Provides slot collection (what details we have vs. need), tag generation, and
recommended clarifying questions so the frontend can prompt users.
"""

from dataclasses import dataclass, field
from typing import Dict, List


REQUIRED_SLOTS = {
    "location": "Which city/area should we search in?",
    "date": "What date do you want the reservation?",
    "time": "What time should we book?",
    "party_size": "How many people?",
    "budget": "Any budget per person or total?",
    "cuisine": "Any cuisine or vibe preference?",
}


@dataclass
class SlotAnalysis:
    slots: Dict[str, str]
    missing_slots: List[str]
    questions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


def analyze_slots(user_prompt: str, provided_slots: Dict[str, str] | None = None) -> SlotAnalysis:
    """Merge provided slots with defaults and list what's missing."""
    provided_slots = provided_slots or {}

    # Normalize keys
    normalized = {k.lower(): str(v) for k, v in provided_slots.items() if v is not None}

    slots: Dict[str, str] = {}
    missing: List[str] = []
    questions: List[str] = []

    for key, question in REQUIRED_SLOTS.items():
        if key in normalized and normalized[key].strip():
            slots[key] = normalized[key].strip()
        else:
            missing.append(key)
            questions.append(question)

    # Tags to guide retrieval
    tags = ["restaurant", "booking"]
    if loc := slots.get("location"):
        tags.append(loc.lower())
    if cuisine := slots.get("cuisine"):
        tags.append(cuisine.lower())

    # Include cue from user prompt so retrievers can incorporate raw intent
    if user_prompt:
        slots["prompt"] = user_prompt.strip()

    return SlotAnalysis(slots=slots, missing_slots=missing, questions=questions, tags=tags)

