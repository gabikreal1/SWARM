#!/usr/bin/env python3
"""Test NeoFS upload/download functionality."""

import asyncio
import json
import os
from src.shared.neofs import get_neofs_client, ObjectAttribute


async def test_neofs():
    """Test NeoFS connection and basic operations."""
    
    # Check environment
    gateway_url = os.getenv("NEOFS_REST_GATEWAY")
    container_id = os.getenv("NEOFS_CONTAINER_ID")
    
    print("🔧 NeoFS Configuration:")
    print(f"   Gateway: {gateway_url}")
    print(f"   Container: {container_id}")
    
    if not gateway_url or not container_id:
        print("\n❌ Missing configuration!")
        print("Add to .env:")
        print("NEOFS_REST_GATEWAY=https://rest.testnet.fs.neo.org")
        print("NEOFS_CONTAINER_ID=<your-container-id>")
        print("\n💡 For hackathon, you need to:")
        print("1. Create your own container (requires Neo N3 testnet GAS)")
        print("2. OR use a public container if available")
        print("3. Public containers may not exist or require different endpoints")
        return
    
    client = get_neofs_client()
    
    try:
        # Test data
        test_data = {
            "message": "Hello from SpoonOS Butler!",
            "timestamp": "2025-12-06",
            "type": "test"
        }
        
        print("\n📤 Uploading test data to NeoFS...")
        result = await client.upload_json(
            test_data,
            filename="test.json",
            additional_attributes=[
                ObjectAttribute(key="Project", value="SpoonOS"),
                ObjectAttribute(key="Environment", value="testnet")
            ]
        )
        
        print(f"✅ Upload successful!")
        print(f"   Container ID: {result.container_id}")
        print(f"   Object ID: {result.object_id}")
        print(f"   URI: neofs://{result.container_id}/{result.object_id}")
        
        # Test download
        print("\n📥 Downloading from NeoFS...")
        downloaded = await client.download_object(
            result.object_id,
            result.container_id
        )
        
        downloaded_data = json.loads(downloaded.decode('utf-8'))
        print(f"✅ Download successful!")
        print(f"   Data: {json.dumps(downloaded_data, indent=2)}")
        
        print("\n🎉 All tests passed! NeoFS is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔍 Common Issues:")
        print("1. Container doesn't exist - create with neofs-cli")
        print("2. Wrong gateway URL - check NeoFS docs for current endpoint")
        print("3. Container ACL not public - set public-read-write when creating")
        print("\n📖 Quick Setup:")
        print("# Get Neo N3 testnet GAS: https://neowish.ngd.network/")
        print("# Create container:")
        print("neofs-cli container create \\")
        print("  --wallet wallet.json \\")
        print("  --rpc-endpoint st1.t5.storage.fs.neo.org:8080 \\")
        print("  --policy 'REP 1 IN X CBF 1 SELECT 1 FROM * AS X' \\")
        print("  --basic-acl public-read-write \\")
        print("  --await")
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_neofs())
