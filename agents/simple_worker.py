"""
Simple Worker Agent
Polls OrderBook for open jobs, places bids, executes tasks, and delivers via NeoFS.
"""
import os
import sys
import time
import random
import json
from dotenv import load_dotenv

# Add SWARM root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.src.shared.contracts import get_contracts, place_bid, register_agent, is_agent_active, setup_event_listener
from neofs_helper import download_job_metadata, upload_job_delivery, compute_content_hash

load_dotenv()

def main():
    print("👷 Starting Simple Worker Agent...")
    
    # Use a different private key for the worker if available, else use the same for demo
    # In production, this MUST be different from the Butler's key
    private_key = os.getenv("WORKER_PRIVATE_KEY") or os.getenv("NEOX_PRIVATE_KEY")
    if not private_key:
        print("❌ No private key found")
        return

    try:
        contracts = get_contracts(private_key)
        print(f"✅ Connected as {contracts.account.address}")
        
        # Register if not active
        # Note: This might fail if the wallet has no GAS
        try:
            if not is_agent_active(contracts, contracts.account.address):
                print("📝 Registering agent...")
                register_agent(contracts, "SimpleWorker", "http://localhost:8000", ["scraping"])
                print("✅ Registered")
        except Exception as e:
            print(f"⚠️ Registration check failed (ignoring): {e}")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return

    def on_job_posted(event):
        job_id = event['args']['jobId']
        poster = event['args']['poster']
        
        if poster == contracts.account.address:
            # Don't bid on own jobs
            return 
            
        print(f"🆕 Job Posted: {job_id} by {poster}")
        
        try:
            # 1. Fetch job details from contract
            job_state, bids = contracts.order_book.functions.getJob(job_id).call()
            # JobState: (id, poster, description, metadataURI, deadline, status, acceptedBid, tags)
            description = job_state[2]
            metadata_uri = job_state[3]
            tags = job_state[7]
            
            print(f"   Description: {description}")
            print(f"   Metadata URI: {metadata_uri}")
            print(f"   Tags: {tags}")
            
            # 2. Download job metadata from NeoFS
            if metadata_uri.startswith("neofs://"):
                print("   📥 Fetching metadata from NeoFS...")
                metadata = download_job_metadata(metadata_uri)
                
                if metadata:
                    print(f"   Tool: {metadata.get('tool', 'unknown')}")
                    print(f"   Parameters: {metadata.get('parameters', {})}")
                else:
                    print("   ⚠️  Failed to fetch metadata, using description only")
            
            # 3. Evaluate if we can do this job
            # In production: Use LLM to evaluate capabilities, cost, feasibility
            can_do_job = True
            
            # For demo: Check if we support the tool
            supported_tools = ["tiktok_scrape", "web_scrape", "data_analysis", "content_generation"]
            if tags:
                tool_tag = tags[0] if isinstance(tags, list) else tags
                if tool_tag not in supported_tools:
                    print(f"   ⏭️  Skipping - unsupported tool: {tool_tag}")
                    return
            
            if not can_do_job:
                print("   ⏭️  Skipping - not in my capability")
                return
            
            # 4. Calculate bid (in production: cost estimation based on task complexity)
            base_price = 5
            complexity_factor = random.uniform(1.0, 2.0)
            price = int(base_price * complexity_factor)
            estimated_time = random.randint(1800, 7200)  # 30min to 2h
            
            # 5. Generate bid metadata
            bid_metadata = {
                "worker": contracts.account.address,
                "capabilities": supported_tools,
                "estimated_cost": price,
                "estimated_time": estimated_time,
                "proposal": f"I can complete this {tags[0] if tags else 'task'} task efficiently."
            }
            metadata_uri = f"neofs://bid-metadata-{job_id}"  # In production: upload to NeoFS
            
            print(f"💸 Bidding {price} USDC (est. {estimated_time}s)...")
            bid_id = place_bid(
                contracts,
                job_id=job_id,
                amount=price,
                estimated_time=estimated_time,
                metadata_uri=metadata_uri
            )
            print(f"✅ Bid Placed: {bid_id}")
            
        except Exception as e:
            print(f"❌ Bid Failed: {e}")

    def on_bid_accepted(event):
        """Handle when our bid is accepted - execute the job"""
        job_id = event['args']['jobId']
        bid_id = event['args']['bidId']
        
        # Check if this is our bid
        try:
            bids = contracts.order_book.functions.getBidsForJob(job_id).call()
            our_bid = None
            
            for bid in bids:
                # Bid: (id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt)
                if bid[0] == bid_id and bid[2] == contracts.account.address:
                    our_bid = bid
                    break
            
            if not our_bid:
                # Not our bid
                return
                
            print(f"\n🎉 Our bid {bid_id} was accepted for job {job_id}!")
            print(f"💼 Starting work...")
            
            # 1. Fetch job metadata
            job_state, _ = contracts.order_book.functions.getJob(job_id).call()
            metadata_uri = job_state[3]
            
            print(f"   📥 Fetching job details from NeoFS...")
            metadata = download_job_metadata(metadata_uri)
            
            if not metadata:
                print("   ❌ Failed to fetch job metadata")
                return
            
            print(f"   Tool: {metadata.get('tool')}")
            print(f"   Parameters: {json.dumps(metadata.get('parameters', {}), indent=2)}")
            
            # 2. Execute the task
            print(f"   🔨 Executing task...")
            time.sleep(2)  # Simulate work
            
            # Simulate task execution
            tool = metadata.get('tool', 'unknown')
            parameters = metadata.get('parameters', {})
            
            # Mock execution results
            result_data = {
                "status": "success",
                "tool": tool,
                "parameters": parameters,
                "output": {
                    "items_scraped": 10,
                    "data": ["item1", "item2", "item3"],
                    "timestamp": time.time()
                },
                "execution_time": 2.5,
                "notes": f"Successfully completed {tool} task"
            }
            
            print(f"   ✅ Task completed!")
            
            # 3. Upload delivery to NeoFS
            print(f"   📤 Uploading delivery to NeoFS...")
            delivery_result = upload_job_delivery(
                job_id=job_id,
                worker=contracts.account.address,
                result_data=result_data
            )
            
            if not delivery_result:
                print("   ❌ Failed to upload delivery to NeoFS")
                return
            
            object_id, delivery_uri, content_hash = delivery_result
            print(f"   ✅ Delivery uploaded: {delivery_uri}")
            print(f"   Hash: {content_hash}")
            
            # 4. Submit delivery to contract
            # Note: In production, call OrderBook.submitDelivery(jobId, deliveryHash)
            # For now, we'll just print what would be submitted
            print(f"\n   📝 Would submit delivery:")
            print(f"      Job ID: {job_id}")
            print(f"      Delivery URI: {delivery_uri}")
            print(f"      Content Hash: {content_hash}")
            print(f"\n   ✅ Work complete! Awaiting payment from escrow...")
            
        except Exception as e:
            print(f"❌ Job execution failed: {e}")
    
    print("👀 Watching for jobs...")
    setup_event_listener(contracts, "JobPosted", on_job_posted)
    
    print("👀 Watching for accepted bids...")
    setup_event_listener(contracts, "BidAccepted", on_bid_accepted)
    
    # Keep alive
    print("\n✨ Worker ready! Waiting for jobs...\n")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
