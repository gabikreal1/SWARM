"""
Test if we can use the public container CeeroywT8ppGE4HGjhpzocJkdb2yu3wD5qCGFTjkw1Cc
"""

import requests
import json

# Public container found on NeoFS
PUBLIC_CONTAINER_ID = "CeeroywT8ppGE4HGjhpzocJkdb2yu3wD5qCGFTjkw1Cc"
NEOFS_GATEWAY = "https://rest.fs.neo.org"

# Test data
test_data = {
    "test": "Butler test upload",
    "timestamp": "2025-12-06T10:00:00Z",
    "purpose": "Testing public container access"
}

print("=" * 60)
print("Testing Public NeoFS Container")
print("=" * 60)
print(f"Container ID: {PUBLIC_CONTAINER_ID}")
print(f"Gateway: {NEOFS_GATEWAY}")
print()

# Get container info
print("--- Step 1: Get Container Info ---")
try:
    response = requests.get(f"{NEOFS_GATEWAY}/v1/containers/{PUBLIC_CONTAINER_ID}")
    if response.status_code == 200:
        info = response.json()
        print(f"✅ Container accessible!")
        print(f"   Owner: {info.get('ownerId')}")
        print(f"   ACL: {info.get('basicAcl')}")
        print(f"   Policy: {info.get('placementPolicy')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Try to upload
print("\n--- Step 2: Try Upload ---")
try:
    # Prepare file
    files = {
        'file': ('test.json', json.dumps(test_data).encode(), 'application/json')
    }
    
    headers = {
        'X-Attribute-FileName': 'butler_test.json',
        'X-Attribute-ContentType': 'application/json',
        'X-Attribute-Type': 'test'
    }
    
    response = requests.post(
        f"{NEOFS_GATEWAY}/v1/objects/{PUBLIC_CONTAINER_ID}",
        files=files,
        headers=headers,
        timeout=30
    )
    
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Upload error: {e}")

print("\n" + "=" * 60)
