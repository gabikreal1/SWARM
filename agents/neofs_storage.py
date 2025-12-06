"""
NeoFS Storage Interface for Butler.

Uses public NeoFS container via REST Gateway for decentralized storage.
"""

import os
import json
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuration
CONTAINER_ID = os.getenv("NEOFS_CONTAINER_ID", "CeeroywT8ppGE4HGjhpzocJkdb2yu3wD5qCGFTjkw1Cc")
NEOFS_GATEWAY = os.getenv("NEOFS_REST_GATEWAY", "https://rest.fs.neo.org")


def upload_json(data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Upload JSON data to NeoFS via REST Gateway.
    
    Args:
        data: Dictionary to upload as JSON
        attributes: Optional metadata attributes
        
    Returns:
        Object ID if successful, None otherwise
    """
    try:
        # Convert to JSON
        content = json.dumps(data, indent=2)
        
        # Prepare multipart file upload
        files = {
            'file': ('data.json', content.encode('utf-8'), 'application/json')
        }
        
        # Prepare headers with attributes
        headers = {}
        if attributes:
            for key, value in attributes.items():
                headers[f'X-Attribute-{key}'] = str(value)
        
        # Add standard attributes
        headers['X-Attribute-FileName'] = 'butler_data.json'
        headers['X-Attribute-ContentType'] = 'application/json'
        
        print(f"📤 Uploading to NeoFS container: {CONTAINER_ID}")
        
        # Upload to NeoFS
        response = requests.post(
            f"{NEOFS_GATEWAY}/v1/objects/{CONTAINER_ID}",
            files=files,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            object_id = result.get('object_id')
            
            if object_id:
                neofs_uri = f"neofs://{CONTAINER_ID}/{object_id}"
                print(f"✅ Uploaded successfully!")
                print(f"   Object ID: {object_id}")
                print(f"   URI: {neofs_uri}")
                return object_id
            else:
                print(f"❌ No object_id in response: {result}")
                return None
        else:
            print(f"❌ Upload failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


def download_json(object_id: str) -> Optional[Dict[str, Any]]:
    """
    Download JSON from NeoFS via REST Gateway.
    
    Args:
        object_id: The object ID
        
    Returns:
        Parsed JSON dict, None if failed
    """
    try:
        print(f"📥 Downloading from NeoFS: {object_id}")
        
        # Download from NeoFS
        response = requests.get(
            f"{NEOFS_GATEWAY}/v1/objects/{CONTAINER_ID}/{object_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            # Parse JSON content
            data = response.json()
            print(f"✅ Downloaded successfully! ({len(response.text)} bytes)")
            return data
        else:
            print(f"❌ Download failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
    except Exception as e:
        print(f"❌ Download error: {e}")
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


def download_from_uri(uri: str) -> Optional[Dict[str, Any]]:
    """
    Download JSON from NeoFS URI.
    
    Args:
        uri: Full NeoFS URI
        
    Returns:
        Parsed JSON dict, None if failed
    """
    parsed = parse_neofs_uri(uri)
    if not parsed:
        print(f"❌ Invalid NeoFS URI: {uri}")
        return None
    
    container_id, object_id = parsed
    return download_json(object_id)


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("NeoFS Storage Test (REST Gateway)")
    print("=" * 60)
    print(f"Container: {CONTAINER_ID}")
    print(f"Gateway: {NEOFS_GATEWAY}")
    print("=" * 60)
    
    # Test data
    test_data = {
        "job_id": 123,
        "description": "Scrape 100 TikTok posts from @elonmusk",
        "requirements": {
            "tool": "tiktok_scrape",
            "username": "@elonmusk",
            "count": 100
        },
        "constraints": {
            "max_time": 3600,
            "budget": 50
        }
    }
    
    print("\n--- Upload Test ---")
    object_id = upload_json(
        data=test_data,
        attributes={"type": "job_metadata", "version": "1.0"}
    )
    
    if object_id:
        print("\n--- Download Test ---")
        retrieved = download_json(object_id)
        
        if retrieved:
            print(f"✅ Success! Data: {json.dumps(retrieved, indent=2)}")
        else:
            print("❌ Download failed")
    
    print("\n" + "=" * 60)
