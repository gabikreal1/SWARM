"""
NeoFS Helper - Upload and download objects using REST Gateway.

This module provides simple functions to interact with your existing NeoFS container.
Includes job metadata handling and delivery verification.
"""

import os
import json
import hashlib
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# NeoFS Configuration
NEOFS_REST_GATEWAY = os.getenv("NEOFS_REST_GATEWAY", "https://rest.fs.neo.org")
CONTAINER_ID = os.getenv("NEOFS_CONTAINER_ID", "9iMKzkCQ7TftU6VVKdVGKJiNq3dsY2K8UoFKWzR53ieK")
OWNER_ADDRESS = "NZ3F1h53bQXjry2QZDzsY2mREYY32h9Mwr"
PRIVATE_KEY_WIF = "L4L2H9Su8dwyfu1QpYnP6NUg3vB1Fg8W25B9jn4Kr8Dfi5ojKFdS"


def upload_object(
    content: str,
    attributes: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None
) -> Optional[str]:
    """
    Upload an object to NeoFS container.
    
    Args:
        content: String content to upload (will be JSON if dict)
        attributes: Optional metadata attributes
        filename: Optional filename
        
    Returns:
        Object ID if successful, None otherwise
    """
    # Convert dict to JSON string
    if isinstance(content, dict):
        content = json.dumps(content, indent=2)
    
    # Prepare attributes
    attrs = attributes or {}
    if filename:
        attrs["FileName"] = filename
    
    # Build attribute headers
    headers = {
        "X-Container-Id": CONTAINER_ID,
        "X-Wallet-Address": OWNER_ADDRESS,
    }
    
    # Add attributes as headers
    for key, value in attrs.items():
        headers[f"X-Attribute-{key}"] = str(value)
    
    try:
        print(f"📤 Uploading to NeoFS container: {CONTAINER_ID}")
        
        # Prepare multipart form data
        files = {
            'file': ('data.json', content.encode('utf-8'), 'application/json')
        }
        
        # Upload object
        response = requests.post(
            f"{NEOFS_REST_GATEWAY}/objects/{CONTAINER_ID}",
            files=files,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            object_id = result.get("object_id") or result.get("oid")
            
            if object_id:
                neofs_uri = f"neofs://{CONTAINER_ID}/{object_id}"
                print(f"✅ Uploaded successfully!")
                print(f"   Object ID: {object_id}")
                print(f"   URI: {neofs_uri}")
                return object_id
            else:
                print(f"❌ Object ID not found in response: {result}")
                return None
        else:
            print(f"❌ Upload failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


def download_object(object_id: str) -> Optional[str]:
    """
    Download an object from NeoFS container.
    
    Args:
        object_id: The NeoFS object ID
        
    Returns:
        Object content as string, None if failed
    """
    try:
        print(f"📥 Downloading from NeoFS: {object_id}")
        
        # Download object
        response = requests.get(
            f"{NEOFS_REST_GATEWAY}/objects/{CONTAINER_ID}/{object_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.text
            print(f"✅ Downloaded successfully! ({len(content)} bytes)")
            return content
        else:
            print(f"❌ Download failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None


def download_object_json(object_id: str) -> Optional[Dict[str, Any]]:
    """
    Download and parse JSON object from NeoFS.
    
    Args:
        object_id: The NeoFS object ID
        
    Returns:
        Parsed JSON dict, None if failed
    """
    content = download_object(object_id)
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            return None
    return None


def parse_neofs_uri(uri: str) -> Optional[tuple[str, str]]:
    """
    Parse NeoFS URI into container ID and object ID.
    
    Args:
        uri: NeoFS URI in format "neofs://{container_id}/{object_id}"
        
    Returns:
        Tuple of (container_id, object_id), None if invalid
    """
    if not uri.startswith("neofs://"):
        return None
    
    parts = uri.replace("neofs://", "").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    return None


def compute_content_hash(content: str) -> str:
    """
    Compute keccak256 hash of content (matches Solidity keccak256).
    
    Args:
        content: String content to hash
        
    Returns:
        Hex string of hash with 0x prefix
    """
    from web3 import Web3
    
    # Convert to bytes and hash
    content_bytes = content.encode('utf-8')
    hash_bytes = Web3.keccak(text=content)
    
    return hash_bytes.hex()


def upload_job_metadata(
    tool: str,
    parameters: Dict[str, Any],
    poster: str,
    requirements: Optional[Dict[str, Any]] = None
) -> Optional[tuple[str, str]]:
    """
    Upload job metadata to NeoFS.
    
    Args:
        tool: Tool/task name
        parameters: Task parameters
        poster: Poster's address
        requirements: Optional requirements dict
        
    Returns:
        Tuple of (object_id, neofs_uri) if successful, None otherwise
    """
    import time
    
    metadata = {
        "tool": tool,
        "parameters": parameters,
        "poster": poster,
        "posted_at": time.time(),
        "requirements": requirements or {
            "quality": "high",
            "format": "json",
            "delivery_time": "24h"
        }
    }
    
    object_id = upload_object(
        content=metadata,
        attributes={
            "type": "job_metadata",
            "tool": tool,
            "poster": poster
        },
        filename=f"job_{int(time.time())}.json"
    )
    
    if object_id:
        neofs_uri = f"neofs://{CONTAINER_ID}/{object_id}"
        return (object_id, neofs_uri)
    
    return None


def upload_job_delivery(
    job_id: int,
    worker: str,
    result_data: Dict[str, Any]
) -> Optional[tuple[str, str, str]]:
    """
    Upload job delivery to NeoFS.
    
    Args:
        job_id: Job ID
        worker: Worker's address
        result_data: Delivery result data
        
    Returns:
        Tuple of (object_id, neofs_uri, content_hash) if successful, None otherwise
    """
    import time
    
    delivery = {
        "job_id": job_id,
        "worker": worker,
        "delivered_at": time.time(),
        "result": result_data
    }
    
    # Convert to JSON string for hashing
    delivery_json = json.dumps(delivery, sort_keys=True, indent=2)
    
    # Compute hash
    content_hash = compute_content_hash(delivery_json)
    
    # Upload to NeoFS
    object_id = upload_object(
        content=delivery,
        attributes={
            "type": "job_delivery",
            "job_id": str(job_id),
            "worker": worker,
            "content_hash": content_hash
        },
        filename=f"delivery_{job_id}_{int(time.time())}.json"
    )
    
    if object_id:
        neofs_uri = f"neofs://{CONTAINER_ID}/{object_id}"
        return (object_id, neofs_uri, content_hash)
    
    return None


def download_job_metadata(metadata_uri: str) -> Optional[Dict[str, Any]]:
    """
    Download and parse job metadata from NeoFS URI.
    
    Args:
        metadata_uri: NeoFS URI
        
    Returns:
        Parsed metadata dict, None if failed
    """
    parsed = parse_neofs_uri(metadata_uri)
    if not parsed:
        print(f"❌ Invalid NeoFS URI: {metadata_uri}")
        return None
    
    container_id, object_id = parsed
    return download_object_json(object_id)


def download_job_delivery(delivery_uri: str) -> Optional[Dict[str, Any]]:
    """
    Download and parse job delivery from NeoFS URI.
    
    Args:
        delivery_uri: NeoFS URI
        
    Returns:
        Parsed delivery dict, None if failed
    """
    parsed = parse_neofs_uri(delivery_uri)
    if not parsed:
        print(f"❌ Invalid NeoFS URI: {delivery_uri}")
        return None
    
    container_id, object_id = parsed
    return download_object_json(object_id)


# Test function
def test_neofs():
    """
    Test NeoFS upload and download.
    """
    print("=" * 60)
    print("Testing NeoFS Operations")
    print("=" * 60)
    print(f"Container: {CONTAINER_ID}")
    print(f"Gateway: {NEOFS_REST_GATEWAY}")
    
    # Test data
    test_data = {
        "test": "Hello from Butler!",
        "timestamp": "2025-12-06T10:00:00Z",
        "data": {
            "field1": "value1",
            "field2": 42
        }
    }
    
    print("\n--- Test 1: Upload JSON ---")
    object_id = upload_object(
        content=test_data,
        attributes={"type": "test", "version": "1.0"},
        filename="test.json"
    )
    
    if object_id:
        print("\n--- Test 2: Download JSON ---")
        retrieved_data = download_object_json(object_id)
        
        if retrieved_data:
            print(f"✅ Test passed! Data matches: {retrieved_data == test_data}")
            print(f"Retrieved: {json.dumps(retrieved_data, indent=2)}")
        else:
            print("❌ Download failed")
    else:
        print("❌ Upload failed")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_neofs()
