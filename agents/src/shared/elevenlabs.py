import os
import logging
from typing import Any, Dict, Optional

import httpx
import websockets
import ssl
import asyncio

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
      - ELEVENLABS_AGENT_ID (for convai signed URL)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        phone_number: Optional[str] = None,
        agent_id: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        # Default to the Twilio outbound-call endpoint if not provided
        self.api_url = api_url or os.getenv("ELEVENLABS_API_URL") or "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID")
        self.phone_number = phone_number or os.getenv("ELEVENLABS_PHONE")
        self.agent_id = agent_id or os.getenv("ELEVENLABS_AGENT_ID")
        self.phone_number_id = phone_number_id or os.getenv("ELEVENLABS_PHONE_NUMBER_ID")

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

    async def get_signed_url(self) -> str:
        """
        Get a signed convai URL for websocket conversation.
        Requires ELEVENLABS_AGENT_ID.
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key missing")
        if not self.agent_id:
            raise ValueError("ELEVENLABS_AGENT_ID missing")

        url = "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url"
        params = {"agent_id": self.agent_id}
        headers = {"xi-api-key": self.api_key}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code >= 300:
                raise RuntimeError(f"get-signed-url failed: {resp.status_code} {resp.text}")
            data = resp.json()
            signed_url = data.get("signed_url")
            if not signed_url:
                raise RuntimeError("Signed URL not returned")
            return signed_url

    async def send_conversation_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy websocket sender (kept for backward compatibility). Prefer send_call.
        """
        signed_url = await self.get_signed_url()
        try:
            # Some environments lack proper root CAs; allow insecure context to avoid handshake failures.
            ssl_ctx = ssl._create_unverified_context()
            async with websockets.connect(signed_url, ping_interval=None, ssl=ssl_ctx) as ws:
                await ws.send(json_dump(payload))
                # Read one response frame (optional)
                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=5)
                except asyncio.TimeoutError:
                    reply = "no-reply"
                return {"status": "sent", "signed_url": signed_url, "reply": reply}
        except Exception as e:
            raise RuntimeError(f"ElevenLabs websocket send failed: {e}")


def json_dump(obj: Dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(obj)
    except Exception:
        return "{}"

