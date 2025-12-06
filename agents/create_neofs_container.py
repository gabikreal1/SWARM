"""
Simple script to create a NeoFS container using SpoonOS tools directly.
No agents needed - just tool calls.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import NeoFS tools from SpoonOS
from spoon_ai.tools.neofs_tools import (
    CreateBearerTokenTool,
    CreateContainerTool,
)


async def create_container():
    """Create a NeoFS container with bearer token"""
    
    print("🚀 Creating NeoFS Container")
    print("=" * 60)
    
    # Initialize tools
    bearer_tool = CreateBearerTokenTool()
    container_tool = CreateContainerTool()
    
    # Step 1: Create bearer token for container creation
    print("\n📝 Step 1: Creating bearer token...")
    try:
        bearer_result = await bearer_tool.execute(
            token_type="container",
            verb="PUT",
            container_id=""  # Empty for container creation
        )
        print(f"✅ Bearer token created")
        print(f"   Token: {bearer_result[:100]}...")  # Show first 100 chars
        
    except Exception as e:
        print(f"❌ Failed to create bearer token: {e}")
        return
    
    # Step 2: Create PUBLIC container
    print("\n📦 Step 2: Creating PUBLIC container...")
    container_name = f"swarm-butler-storage"
    
    try:
        container_result = await container_tool.execute(
            name=container_name,
            bearer_token=bearer_result,
            basic_acl="public-read-write",  # PUBLIC container (no tokens needed for upload/download)
            placement_policy="REP 1",
            attributes_json='{"project": "SWARM", "environment": "hackathon", "type": "public"}'
        )
        
        print(f"✅ Container created successfully!")
        print(f"   Name: {container_name}")
        print(f"   Container ID: {container_result}")
        print(f"   Type: PUBLIC (no bearer tokens needed for uploads)")
        
        # Show environment variable to add
        print(f"\n📋 Add to agents/.env:")
        print(f"   NEOFS_CONTAINER_ID={container_result}")
        print(f"   NEOFS_GATEWAY_URL=https://rest.fs.neo.org")
        
        return container_result
        
    except Exception as e:
        print(f"❌ Failed to create container: {e}")
        return None


async def create_eacl_container():
    """Create an eACL container (requires bearer tokens for all operations)"""
    
    print("\n🔒 Creating eACL Container (with access control)")
    print("=" * 60)
    
    bearer_tool = CreateBearerTokenTool()
    container_tool = CreateContainerTool()
    
    # Step 1: Create bearer token
    print("\n📝 Step 1: Creating bearer token...")
    try:
        bearer_result = await bearer_tool.execute(
            token_type="container",
            verb="PUT",
            container_id=""
        )
        print(f"✅ Bearer token created")
        
    except Exception as e:
        print(f"❌ Failed to create bearer token: {e}")
        return
    
    # Step 2: Create eACL container
    print("\n📦 Step 2: Creating eACL container...")
    container_name = f"swarm-butler-secure"
    
    try:
        container_result = await container_tool.execute(
            name=container_name,
            bearer_token=bearer_result,
            basic_acl="eacl-public-read-write",  # eACL container (requires tokens for all ops)
            placement_policy="REP 1",
            attributes_json='{"project": "SWARM", "environment": "production", "type": "eacl", "security": "high"}'
        )
        
        print(f"✅ eACL Container created successfully!")
        print(f"   Name: {container_name}")
        print(f"   Container ID: {container_result}")
        print(f"   Type: eACL (bearer tokens REQUIRED for all operations)")
        
        print(f"\n⚠️  Note: You'll need bearer tokens for:")
        print(f"   - Uploading objects (operation=PUT)")
        print(f"   - Downloading objects (operation=GET)")
        print(f"   - Setting eACL rules (verb=SETEACL)")
        
        return container_result
        
    except Exception as e:
        print(f"❌ Failed to create container: {e}")
        return None


async def main():
    """Create both PUBLIC and eACL containers"""
    
    print("\n🌟 NeoFS Container Creation Script")
    print("=" * 80)
    print("Using SpoonOS NeoFS tools directly (no agents needed)")
    print("=" * 80)
    
    # Check environment
    if not os.getenv("NEOX_PRIVATE_KEY"):
        print("\n❌ NEOX_PRIVATE_KEY not set in .env")
        print("   Add your Neo N3 wallet private key to agents/.env")
        return
    
    print("\nℹ️  Prerequisites:")
    print("   ✅ NEOX_PRIVATE_KEY set in .env")
    print("   ✅ SpoonOS neofs_tools installed")
    print("   ✅ Network: Neo N3 Testnet")
    
    # Create PUBLIC container (recommended for hackathon)
    public_container_id = await create_container()
    
    # Optionally create eACL container
    print("\n" + "=" * 80)
    create_eacl = input("\nCreate eACL container too? (y/n): ").lower().strip()
    if create_eacl == 'y':
        eacl_container_id = await create_eacl_container()
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ Container Creation Complete!")
    print("=" * 80)
    
    if public_container_id:
        print(f"\n📦 PUBLIC Container: {public_container_id}")
        print(f"   Use for: Job metadata, delivery results")
        print(f"   Benefits: No bearer tokens needed for uploads/downloads")
    
    print("\n💡 Next Steps:")
    print("   1. Add NEOFS_CONTAINER_ID to agents/.env")
    print("   2. Use in Butler: upload job details before posting to OrderBook")
    print("   3. Use in Agents: upload delivery results after completing jobs")


if __name__ == "__main__":
    asyncio.run(main())
