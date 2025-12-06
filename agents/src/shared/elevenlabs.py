import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ElevenLabsClient:
    """
    Minimal ElevenLabs JSON caller.

    Expects:
      - ELEVENLABS_API_URL: full endpoint to post call/job data
      - ELEVENLABS_API_KEY: secret key for header `xi-api-key`
    Optional:
      - ELEVENLABS_VOICE_ID
      - ELEVENLABS_PHONE
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        phone_number: Optional[str] = None,
    ):
        self.api_url = api_url or os.getenv("ELEVENLABS_API_URL")
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
        self.phone_number = phone_number or os.getenv("ELEVENLABS_PHONE")

    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    async def send_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise ValueError("ElevenLabs client not configured (API URL or API KEY missing)")

        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.api_url, json=payload, headers=headers)
            if resp.status_code >= 300:
                text = resp.text
                raise RuntimeError(f"ElevenLabs call failed: {resp.status_code} {resp.reason_phrase} {text}")
            try:
                return resp.json()
            except Exception:
                return {"status": "ok", "raw": resp.text}

