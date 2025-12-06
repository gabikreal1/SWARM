"""
Create a public NeoFS container using REST Gateway.

This script uses the NeoFS REST Gateway to create a public container
that can be used by the Butler and worker agents.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# NeoFS Configuration
NEOFS_REST_GATEWAY = "https://rest.fs.neo.org"
OWNER_ADDRESS = "NZ3F1h53bQXjry2QZDzsY2mREYY32h9Mwr"
PRIVATE_KEY_WIF = "L4L2H9Su8dwyfu1QpYnP6NUg3vB1Fg8W25B9jn4Kr8Dfi5ojKFdS"


def create_public_container():
    """
    Create a public NeoFS container for Butler job data using REST Gateway.
    
    Returns:
        str: Container ID if successful, None otherwise
    """
    print("🚀 Creating public NeoFS container via REST Gateway...")
    print(f"   Gateway: {NEOFS_REST_GATEWAY}")
    print(f"   Owner: {OWNER_ADDRESS}")
    
    # Container creation payload (attributes must be array of key-value pairs)
    container_data = {
        "containerName": "butler-jobs",
        "placementPolicy": "REP 1",  # Single replica
        "basicAcl": "public-read-write",  # Public access
        "attributes": [
            {"key": "purpose", "value": "SpoonOS Butler job metadata and results"},
            {"key": "created_by", "value": "butler_setup"},
            {"key": "access", "value": "public"},
            {"key": "version", "value": "1.0"}
        ]
    }
    
    # Headers for authentication
    headers = {
        "Content-Type": "application/json",
        "X-Wallet-Address": OWNER_ADDRESS,
        "X-Wallet-WIF": PRIVATE_KEY_WIF
    }
    
    try:
        print("\n📦 Sending container creation request...")
        
        # POST to NeoFS REST Gateway
        response = requests.post(
            f"{NEOFS_REST_GATEWAY}/v1/containers",
            json=container_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            container_id = result.get("containerId") or result.get("container_id")
            
            if container_id:
                print(f"✅ Container created successfully!")
                print(f"\n📋 Container ID: {container_id}")
                print(f"\n🔗 Container URI format: neofs://{container_id}/<object_id>")
                return container_id
            else:
                print(f"❌ Container ID not found in response: {result}")
                return None
        else:
            print(f"❌ Failed to create container: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        print("\nPossible issues:")
        print("  - NeoFS REST Gateway may be unavailable")
        print("  - Network connectivity issues")
        print("  - Invalid credentials")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def update_env_file(container_id: str):
    """
    Update .env file with the new container ID.
    
    Args:
        container_id: The NeoFS container ID to add to .env
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    print(f"\n💾 Updating {env_path}...")
    
    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Find and update NEOFS_CONTAINER_ID line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('NEOFS_CONTAINER_ID='):
                lines[i] = f'NEOFS_CONTAINER_ID={container_id}\n'
                updated = True
                break
        
        # If not found, add it
        if not updated:
            lines.append(f'\nNEOFS_CONTAINER_ID={container_id}\n')
        
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
        print(f"✅ Updated .env with container ID")
        
    except Exception as e:
        print(f"❌ Failed to update .env: {e}")
        print(f"\n⚠️  Please manually add this line to your .env file:")
        print(f"NEOFS_CONTAINER_ID={container_id}")


def main():
    print("=" * 60)
    print("SpoonOS NeoFS Container Creator")
    print("=" * 60)
    
    # Check if container already exists in env
    existing_container = os.getenv("NEOFS_CONTAINER_ID")
    if existing_container and existing_container.strip():
        print(f"\n⚠️  Container ID already exists in .env:")
        print(f"   {existing_container}")
        
        choice = input("\nCreate a new container anyway? (y/N): ").lower()
        if choice != 'y':
            print("✋ Keeping existing container. Exiting.")
            return
    
    # Create container
    container_id = create_public_container()
    
    if container_id:
        # Update .env file
        update_env_file(container_id)
        
        print("\n" + "=" * 60)
        print("✅ Setup complete!")
        print("=" * 60)
        print(f"\nYour Butler can now use NeoFS storage:")
        print(f"  Container ID: {container_id}")
        print(f"  Access: Public (anyone can read/write)")
        print(f"  Policy: REP 1 (single replica)")
        print(f"\nNext steps:")
        print(f"  1. Start Butler API: python spoonos_butler_api.py")
        print(f"  2. Start worker agent: python simple_worker.py")
        print(f"  3. Test with ElevenLabs voice agent")
    else:
        print("\n" + "=" * 60)
        print("❌ Container creation failed")
        print("=" * 60)
        print("\nYou can:")
        print("  1. Check SpoonOS documentation for NeoFS setup")
        print("  2. Create container via NeoFS GUI and add ID to .env manually")
        print("  3. Contact SpoonOS support if issues persist")


if __name__ == "__main__":
    main()
