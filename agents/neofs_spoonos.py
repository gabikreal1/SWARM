"""
NeoFS Helper using SpoonOS SDK.

Simple wrapper around SpoonOS neofs_tools for Butler integration.
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Try to import SpoonOS tools
try:
    from spoon_ai.tools.neofs_tools import (
        UploadObjectTool,
        DownloadObjectByIdTool,
        DownloadObjectByAttributeTool
    )
    SPOONOS_AVAILABLE = True
except ImportError:
    SPOONOS_AVAILABLE = False
    print("⚠️  SpoonOS not installed. Install with: pip install spoon-ai")


# Configuration
CONTAINER_ID = os.getenv("NEOFS_CONTAINER_ID", "9iMKzkCQ7TftU6VVKdVGKJiNq3dsY2K8UoFKWzR53ieK")


def upload_json(data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Upload JSON data to NeoFS.
    
    Args:
        data: Dictionary to upload as JSON
        attributes: Optional metadata attributes
        
    Returns:
        Object ID if successful, None otherwise
    """
    if not SPOONOS_AVAILABLE:
        print("❌ SpoonOS not available")
        return None
    
    try:
        upload_tool = UploadObjectTool()
        
        # Convert data to JSON string
        content = json.dumps(data, indent=2)
        
        # Prepare attributes
        attrs = attributes or {}
        attrs_json = json.dumps(attrs)
        
        print(f"📤 Uploading to NeoFS container: {CONTAINER_ID}")
        
        # Upload
        object_id = upload_tool.execute(
            container_id=CONTAINER_ID,
            content=content,
            attributes_json=attrs_json
        )
        
        if object_id:
            neofs_uri = f"neofs://{CONTAINER_ID}/{object_id}"
            print(f"✅ Uploaded successfully!")
            print(f"   Object ID: {object_id}")
            print(f"   URI: {neofs_uri}")
            return object_id
        else:
            print("❌ Upload returned no object ID")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


def download_json(object_id: str) -> Optional[Dict[str, Any]]:
    """
    Download and parse JSON from NeoFS.
    
    Args:
        object_id: The NeoFS object ID
        
    Returns:
        Parsed JSON dict, None if failed
    """
    if not SPOONOS_AVAILABLE:
        print("❌ SpoonOS not available")
        return None
    
    try:
        download_tool = DownloadObjectByIdTool()
        
        print(f"📥 Downloading from NeoFS: {object_id}")
        
        # Download
        content = download_tool.execute(
            container_id=CONTAINER_ID,
            object_id=object_id
        )
        
        if content:
            print(f"✅ Downloaded successfully! ({len(content)} bytes)")
            # Parse JSON
            data = json.loads(content)
            return data
        else:
            print("❌ Download returned no content")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
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
        uri: Full NeoFS URI like "neofs://{container_id}/{object_id}"
        
    Returns:
        Parsed JSON dict, None if failed
    """
    parsed = parse_neofs_uri(uri)
    if not parsed:
        print(f"❌ Invalid NeoFS URI: {uri}")
        return None
    
    container_id, object_id = parsed
    
    # Override global container ID temporarily
    global CONTAINER_ID
    original_container = CONTAINER_ID
    CONTAINER_ID = container_id
    
    try:
        return download_json(object_id)
    finally:
        CONTAINER_ID = original_container


# Test function
def test_neofs():
    """
    Test NeoFS upload and download with SpoonOS.
    """
    if not SPOONOS_AVAILABLE:
        print("❌ Cannot test: SpoonOS not installed")
        print("Install with: pip install spoon-ai")
        return
    
    print("=" * 60)
    print("Testing NeoFS with SpoonOS SDK")
    print("=" * 60)
    print(f"Container: {CONTAINER_ID}")
    
    # Test data
    test_data = {
        "test": "Hello from Butler!",
        "timestamp": "2025-12-06T10:00:00Z",
        "job_requirements": {
            "tool": "tiktok_scrape",
            "username": "@elonmusk",
            "count": 100
        }
    }
    
    print("\n--- Test 1: Upload JSON ---")
    object_id = upload_json(
        data=test_data,
        attributes={"type": "test_job", "version": "1.0"}
    )
    
    if object_id:
        print("\n--- Test 2: Download JSON ---")
        retrieved_data = download_json(object_id)
        
        if retrieved_data:
            matches = retrieved_data == test_data
            print(f"✅ Test passed! Data matches: {matches}")
            if not matches:
                print(f"Expected: {test_data}")
                print(f"Got: {retrieved_data}")
        else:
            print("❌ Download failed")
    else:
        print("❌ Upload failed")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_neofs()
