"""
NeoFS REST Gateway Client

Uses the NeoFS REST Gateway API for decentralized storage.
"""

import os
import json
import base64
import time
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel


@dataclass
class NeoFSConfig:
    """NeoFS configuration"""
    gateway_url: str
    container_id: Optional[str] = None


class ObjectAttribute(BaseModel):
    """NeoFS object attribute"""
    key: str
    value: str


class UploadResult(BaseModel):
    """Result of object upload"""
    object_id: str
    container_id: str


class NeoFSObject(BaseModel):
    """NeoFS object metadata"""
    object_id: str
    container_id: str
    attributes: list[ObjectAttribute]
    size: int


class NeoFSClient:
    """
    NeoFS REST Gateway client.
    
    Uses the REST Gateway (HTTP Gateway is deprecated).
    """
    
    def __init__(self, config: NeoFSConfig):
        self.gateway_url = config.gateway_url.rstrip('/')
        self.container_id = config.container_id
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def upload_object(
        self,
        data: bytes | str,
        attributes: list[ObjectAttribute] | None = None,
        container_id: str | None = None
    ) -> UploadResult:
        """Upload data to NeoFS via REST POST /v1/objects/{cid}."""

        cid = container_id or self.container_id
        if not cid:
            raise ValueError("Container ID is required")

        # Convert to base64 if string
        if isinstance(data, str):
            data = data.encode('utf-8')
        payload_b64 = base64.b64encode(data).decode('ascii')

        # Build attributes dict
        attrs_dict = {}
        if attributes:
            for attr in attributes:
                attrs_dict[attr.key] = attr.value

        response = await self.client.post(
            f"{self.gateway_url}/v1/objects/{cid}",
            json={
                "payload": payload_b64,
                "attributes": attrs_dict,
            },
        )
        response.raise_for_status()

        result = response.json()
        object_id = result.get("object_id") or result.get("oid")
        return UploadResult(
            object_id=object_id or "",
            container_id=cid
        )
    
    async def download_object(
        self,
        object_id: str,
        container_id: str | None = None
    ) -> bytes:
        """
        Download object from NeoFS.
        
        Args:
            object_id: Object ID to download
            container_id: Override default container ID
            
        Returns:
            Object data as bytes
        """
        cid = container_id or self.container_id
        if not cid:
            raise ValueError("Container ID is required")
        
        response = await self.client.get(
            f"{self.gateway_url}/v1/objects/{cid}/by_id/{object_id}"
        )
        response.raise_for_status()

        result = response.json()
        payload_b64 = result.get("payload")
        if payload_b64 is None:
            raise ValueError("Payload missing in NeoFS response")
        return base64.b64decode(payload_b64)
    
    async def search_objects(
        self,
        filters: dict[str, str],
        container_id: str | None = None
    ) -> list[NeoFSObject]:
        """
        Search for objects in container.
        
        Args:
            filters: Key-value filters for search
            container_id: Override default container ID
            
        Returns:
            List of matching objects
        """
        cid = container_id or self.container_id
        if not cid:
            raise ValueError("Container ID is required")
        
        filter_list = [
            {"key": k, "match": "STRING_EQUAL", "value": v}
            for k, v in filters.items()
        ]
        
        response = await self.client.post(
            f"{self.gateway_url}/v1/objects/{cid}/search",
            json={"filters": filter_list}
        )
        response.raise_for_status()
        
        result = response.json()
        return [
            NeoFSObject(
                object_id=obj.get("object_id", ""),
                container_id=cid,
                attributes=[
                    ObjectAttribute(key=k, value=v)
                    for k, v in obj.get("attributes", {}).items()
                ],
                size=obj.get("size", 0)
            )
            for obj in result.get("objects", [])
        ]
    
    async def upload_json(
        self,
        data: Any,
        filename: str,
        additional_attributes: list[ObjectAttribute] | None = None,
        container_id: str | None = None
    ) -> UploadResult:
        """
        Upload JSON data with proper attributes.
        
        Args:
            data: JSON-serializable data
            filename: Filename for the object
            additional_attributes: Extra attributes to add
            container_id: Override default container ID
            
        Returns:
            UploadResult
        """
        json_string = json.dumps(data, indent=2)
        
        attributes = [
            ObjectAttribute(key="FileName", value=filename),
            ObjectAttribute(key="ContentType", value="application/json"),
            ObjectAttribute(key="Timestamp", value=datetime.utcnow().isoformat()),
        ]
        if additional_attributes:
            attributes.extend(additional_attributes)
        
        return await self.upload_object(json_string, attributes, container_id)
    
    async def upload_scraping_results(
        self,
        results: Any,
        job_id: str | int,
        source: str
    ) -> UploadResult:
        """
        Upload scraping results with standard attributes.
        
        Args:
            results: Scraping results (JSON-serializable)
            job_id: Job ID
            source: Source identifier (e.g., "tiktok", "web")
            
        Returns:
            UploadResult
        """
        import time
        filename = f"scrape-{job_id}-{int(time.time())}.json"
        
        return await self.upload_json(
            results,
            filename,
            [
                ObjectAttribute(key="Type", value="scrape_result"),
                ObjectAttribute(key="JobId", value=str(job_id)),
                ObjectAttribute(key="Source", value=source),
            ]
        )
    
    async def upload_call_result(
        self,
        result: Any,
        job_id: str | int,
        phone_number: str
    ) -> UploadResult:
        """
        Upload call recording/result with standard attributes.
        
        Args:
            result: Call result (JSON-serializable)
            job_id: Job ID
            phone_number: Called phone number
            
        Returns:
            UploadResult
        """
        import time
        filename = f"call-{job_id}-{int(time.time())}.json"
        
        return await self.upload_json(
            result,
            filename,
            [
                ObjectAttribute(key="Type", value="call_result"),
                ObjectAttribute(key="JobId", value=str(job_id)),
                ObjectAttribute(key="PhoneNumber", value=phone_number),
            ]
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def upload_job_metadata(
    metadata: Any,
    tags: list[str] | None = None,
    *,
    filename_prefix: str = "job-metadata",
) -> str:
    """
    Upload job metadata document to NeoFS and return URI.

    Args:
        metadata: JSON-serializable metadata payload.
        tags: Optional tags to store alongside the object for discovery.
        filename_prefix: Prefix for generated filename.
    """
    client = get_neofs_client()
    timestamp = int(time.time())
    attributes = [
        ObjectAttribute(key="Type", value="job_metadata"),
        ObjectAttribute(key="Timestamp", value=datetime.utcnow().isoformat()),
    ]
    if tags:
        attributes.append(ObjectAttribute(key="Tags", value=",".join(tags)))

    result = await client.upload_json(
        metadata,
        filename=f"{filename_prefix}-{timestamp}.json",
        additional_attributes=attributes,
    )
    await client.close()
    return f"neofs://{result.container_id}/{result.object_id}"


def get_neofs_client() -> NeoFSClient:
    """Get default NeoFS client from environment"""
    return NeoFSClient(NeoFSConfig(
        gateway_url=os.getenv("NEOFS_REST_GATEWAY", "http://rest.t5.fs.neo.org:8080"),
        container_id=os.getenv("NEOFS_CONTAINER_ID"),
    ))
