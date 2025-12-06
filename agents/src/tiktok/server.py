"""
TikTok Scraper Agent API

Lightweight FastAPI service that exposes a TikTok search endpoint backed by
the SpoonOS TikTok search tool. This is independent from the Butler API.
"""
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from .tool import TikTokSearchTool

app = FastAPI(title="TikTok Scraper Agent", version="0.1.0")


class TikTokSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    location: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "tiktok_scraper"}


@app.post("/tiktok/search")
async def tiktok_search(payload: TikTokSearchRequest):
    tool = TikTokSearchTool()
    try:
        raw = await tool.execute(
            query=payload.query,
            max_results=payload.max_results,
            location=payload.location,
        )
        data = json.loads(raw)
        if not data.get("success"):
            raise HTTPException(status_code=500, detail=data.get("error", "Scrape failed"))
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run():
    port = 3010
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
