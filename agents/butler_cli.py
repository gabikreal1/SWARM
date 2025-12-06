"""
Butler CLI - Interactive CLI for SpoonOS Butler Agent
Complete job lifecycle: inquire → quote → confirm → track delivery

Features:
- Interactive conversation with slot filling
- NeoFS integration for job metadata and delivery
- Real-time bid monitoring
- Delivery tracking
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Add SWARM root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to import SlotFiller, but gracefully handle if dependencies are missing
try:
    from agents.src.shared.slot_questioning import SlotFiller
    SLOT_FILLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  SlotFiller not available: {e}")
    print("   Continuing with basic slot filling...")
    SLOT_FILLER_AVAILABLE = False
    SlotFiller = None

from agents.src.shared.contracts import get_contracts, approve_usdc, post_job, get_bids_for_job, accept_bid, ContractInstances
from neofs_helper import upload_object, download_object_json, parse_neofs_uri

load_dotenv()


class ButlerCLI:
    """Interactive Butler Agent CLI with full NeoFS integration"""
    
    def __init__(self):
        self.contracts: Optional[ContractInstances] = None
        self.slot_filler: Optional[Any] = None  # SlotFiller or None
        self.user_id = "cli_user"
        self.conversation_history = []
        
        # Current job state
        self.current_tool = None
        self.current_slots = {}
        self.current_job_id = None
        self.current_bid_id = None
        
        # Define available tools
        self.candidate_tools = [
            {
                "name": "tiktok_scrape",
                "description": "Scrape TikTok posts from a user profile",
                "required_params": ["username", "count"]
            },
            {
                "name": "web_scrape",
                "description": "Scrape content from any website",
                "required_params": ["url"]
            },
            {
                "name": "data_analysis",
                "description": "Analyze data and generate insights",
                "required_params": ["data_source", "analysis_type"]
            },
            {
                "name": "content_generation",
                "description": "Generate content based on requirements",
                "required_params": ["content_type", "topic", "length"]
            }
        ]
        
    def initialize(self):
        """Initialize all components"""
        print("🤖 SpoonOS Butler Agent")
        print("=" * 60)
        
        # Initialize blockchain contracts
        private_key = os.getenv("NEOX_PRIVATE_KEY")
        if not private_key:
            print("❌ NEOX_PRIVATE_KEY not found in .env")
            print("   Please set your private key to use blockchain features")
            return False
            
        try:
            print("🔗 Connecting to NeoX blockchain...")
            self.contracts = get_contracts(private_key)
            print(f"✅ Connected as {self.contracts.account.address}")
            
            # Auto-approve USDC for Escrow
            usdc_address = self.contracts.usdc.address
            escrow_address = self.contracts.escrow.address
            allowance = self.contracts.usdc.functions.allowance(
                self.contracts.account.address, 
                escrow_address
            ).call()
            
            if allowance < 1000 * 10**6:
                print("🔄 Approving USDC for Escrow...")
                approve_usdc(self.contracts, escrow_address, 2**256 - 1)
                print("✅ USDC Approved")
                
        except Exception as e:
            print(f"❌ Blockchain connection failed: {e}")
            return False
            
        # Initialize slot filler if available
        if SLOT_FILLER_AVAILABLE and SlotFiller:
            try:
                print("🧠 Initializing AI components...")
                self.slot_filler = SlotFiller(user_id=self.user_id)
                print("✅ SlotFiller ready")
            except Exception as e:
                print(f"⚠️  SlotFiller initialization failed: {e}")
                print("   Continuing with basic slot filling...")
        else:
            print("ℹ️  Using basic slot filling (advanced AI components not available)")
            
        # Test NeoFS
        try:
            print("📦 Testing NeoFS connection...")
            test_data = {"test": "butler_init", "timestamp": time.time()}
            test_oid = upload_object(
                content=test_data,
                attributes={"type": "test", "source": "butler_cli"},
                filename="test.json"
            )
            if test_oid:
                print(f"✅ NeoFS ready (test object: {test_oid[:16]}...)")
            else:
                print("⚠️  NeoFS upload test failed")
        except Exception as e:
            print(f"⚠️  NeoFS test failed: {e}")
            
        print("=" * 60)
        print()
        return True
        
    def process_user_input(self, user_message: str) -> Dict[str, Any]:
        """Process user input and determine next action"""
        
        # Special commands
        if user_message.lower() in ['exit', 'quit', 'bye']:
            return {"action": "exit", "message": "Goodbye! 👋"}
            
        if user_message.lower() in ['help', '?']:
            return {
                "action": "help",
                "message": self.get_help_message()
            }
            
        if user_message.lower() == 'status' and self.current_job_id:
            return {"action": "status"}
            
        # If we're collecting slots, update them
        if self.current_tool and self.conversation_history:
            # Parse the response for slot values
            self.extract_slots_from_message(user_message)
            
        # Use SlotFiller to determine what we need
        if self.slot_filler:
            try:
                missing_slots, questions, chosen_tool = self.slot_filler.fill(
                    user_message=user_message,
                    current_slots=self.current_slots,
                    candidate_tools=self.candidate_tools
                )
                
                self.current_tool = chosen_tool
                
                if missing_slots:
                    question = questions[0] if questions else f"What is the {missing_slots[0]}?"
                    return {
                        "action": "question",
                        "message": question,
                        "missing_slots": missing_slots
                    }
                else:
                    # All slots filled, ready to post job
                    return {
                        "action": "confirm",
                        "message": self.format_confirmation()
                    }
                    
            except Exception as e:
                print(f"⚠️  SlotFiller error: {e}")
                # Fall through to basic extraction
                
        # Basic fallback slot extraction
        return self.basic_slot_extraction(user_message)
        
    def extract_slots_from_message(self, message: str):
        """Extract slot values from user message"""
        # Simple extraction patterns
        import re
        
        # Username extraction (Twitter, TikTok, Instagram handles)
        username_match = re.search(r'@(\w+)', message)
        if username_match and 'username' not in self.current_slots:
            self.current_slots['username'] = username_match.group(1)
            
        # URL extraction
        url_match = re.search(r'https?://[^\s]+', message)
        if url_match and 'url' not in self.current_slots:
            self.current_slots['url'] = url_match.group(0)
            
        # Number extraction (count, length, etc.)
        numbers = re.findall(r'\b(\d+)\b', message)
        if numbers:
            if 'count' in str(self.current_tool) and 'count' not in self.current_slots:
                self.current_slots['count'] = int(numbers[0])
            elif 'length' in str(self.current_tool) and 'length' not in self.current_slots:
                self.current_slots['length'] = int(numbers[0])
                
    def basic_slot_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback basic slot extraction without SlotFiller"""
        # Detect intent
        message_lower = message.lower()
        
        if 'tiktok' in message_lower or 'scrape' in message_lower:
            self.current_tool = 'tiktok_scrape'
            self.extract_slots_from_message(message)
            
            missing = []
            if 'username' not in self.current_slots:
                missing.append('username')
            if 'count' not in self.current_slots:
                missing.append('count')
                
            if missing:
                questions = {
                    'username': "What TikTok username would you like me to scrape?",
                    'count': "How many posts should I scrape?"
                }
                return {
                    "action": "question",
                    "message": questions.get(missing[0], f"What is the {missing[0]}?"),
                    "missing_slots": missing
                }
            else:
                return {
                    "action": "confirm",
                    "message": self.format_confirmation()
                }
                
        return {
            "action": "question",
            "message": "I can help you with TikTok scraping, web scraping, data analysis, or content generation. What would you like to do?"
        }
        
    def format_confirmation(self) -> str:
        """Format confirmation message for user"""
        slots_str = json.dumps(self.current_slots, indent=2)
        return (
            f"Great! I have all the details:\n\n"
            f"📋 Task: {self.current_tool}\n"
            f"📝 Parameters:\n{slots_str}\n\n"
            f"Shall I post this job to the marketplace and get quotes from agents? (yes/no)"
        )
        
    def post_job_with_neofs(self) -> Dict[str, Any]:
        """Post job with NeoFS metadata"""
        if not self.contracts:
            return {"success": False, "error": "Blockchain not connected"}
            
        # 1. Create job metadata
        job_metadata = {
            "tool": self.current_tool,
            "parameters": self.current_slots,
            "requirements": {
                "quality": "high",
                "format": "json",
                "delivery_time": "24h"
            },
            "posted_by": self.contracts.account.address,
            "posted_at": time.time()
        }
        
        # 2. Upload to NeoFS
        print("📤 Uploading job metadata to NeoFS...")
        try:
            object_id = upload_object(
                content=job_metadata,
                attributes={
                    "type": "job_metadata",
                    "tool": self.current_tool,
                    "poster": self.contracts.account.address
                },
                filename=f"job_{int(time.time())}.json"
            )
            
            if not object_id:
                return {"success": False, "error": "Failed to upload metadata to NeoFS"}
                
            metadata_uri = f"neofs://{os.getenv('NEOFS_CONTAINER_ID')}/{object_id}"
            print(f"✅ Metadata uploaded: {metadata_uri}")
            
        except Exception as e:
            return {"success": False, "error": f"NeoFS upload failed: {e}"}
            
        # 3. Post job to blockchain
        print("📤 Posting job to OrderBook...")
        try:
            description = f"{self.current_tool}: {json.dumps(self.current_slots)}"
            tags = [self.current_tool, "cli"]
            deadline = int(time.time()) + 86400  # 24 hours
            
            job_id = post_job(
                self.contracts,
                description=description,
                metadata_uri=metadata_uri,
                tags=tags,
                deadline=deadline
            )
            
            self.current_job_id = job_id
            print(f"✅ Job posted! Job ID: {job_id}")
            
            return {
                "success": True,
                "job_id": job_id,
                "metadata_uri": metadata_uri
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to post job: {e}"}
            
    def wait_for_bids(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Wait for bids and return them"""
        print(f"⏳ Waiting for bids ({timeout}s)...")
        
        start_time = time.time()
        last_bid_count = 0
        
        while time.time() - start_time < timeout:
            try:
                bids = get_bids_for_job(self.contracts, self.current_job_id)
                
                if len(bids) > last_bid_count:
                    print(f"💰 Received {len(bids)} bid(s)...")
                    last_bid_count = len(bids)
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️  Error checking bids: {e}")
                
        # Final check
        try:
            bids = get_bids_for_job(self.contracts, self.current_job_id)
            print(f"\n📊 Total bids received: {len(bids)}")
            
            formatted_bids = []
            for bid in bids:
                # Bid struct: (id, jobId, bidder, price, deliveryTime, reputation, metadataURI, responseURI, accepted, createdAt)
                formatted_bids.append({
                    "id": bid[0],
                    "bidder": bid[2],
                    "price": bid[3],
                    "delivery_time": bid[4],
                    "reputation": bid[5],
                    "metadata_uri": bid[6]
                })
                
            return formatted_bids
            
        except Exception as e:
            print(f"❌ Failed to fetch bids: {e}")
            return []
            
    def display_bids(self, bids: List[Dict[str, Any]]):
        """Display bids in a nice format"""
        if not bids:
            print("❌ No bids received yet.")
            return
            
        print("\n" + "=" * 60)
        print("💰 Available Bids")
        print("=" * 60)
        
        # Sort by price
        sorted_bids = sorted(bids, key=lambda x: x['price'])
        
        for i, bid in enumerate(sorted_bids, 1):
            print(f"\n#{i} - Bid ID: {bid['id']}")
            print(f"   Agent: {bid['bidder'][:10]}...{bid['bidder'][-8:]}")
            print(f"   Price: {bid['price']} USDC")
            print(f"   Delivery Time: {bid['delivery_time']}s ({bid['delivery_time']//3600}h)")
            print(f"   Reputation: {bid['reputation']}")
            
        print("\n" + "=" * 60)
        
        # Recommend best bid
        best_bid = sorted_bids[0]
        self.current_bid_id = best_bid['id']
        
        print(f"\n💡 Recommended: Bid #{1} for {best_bid['price']} USDC")
        print(f"   (Lowest price)")
        
    def accept_bid_and_track(self, bid_id: Optional[int] = None):
        """Accept bid and track delivery"""
        if bid_id is None:
            bid_id = self.current_bid_id
            
        if not bid_id:
            print("❌ No bid selected")
            return
            
        print(f"\n🤝 Accepting bid {bid_id}...")
        
        try:
            tx = accept_bid(
                self.contracts,
                job_id=self.current_job_id,
                bid_id=bid_id,
                response_uri="neofs://accepted"
            )
            
            print(f"✅ Bid accepted! Transaction: {tx[:16]}...")
            print(f"💰 Funds locked in escrow")
            print(f"\n📦 Agent is now working on your task...")
            print(f"   Job ID: {self.current_job_id}")
            print(f"   You can check status anytime by typing 'status'")
            
        except Exception as e:
            print(f"❌ Failed to accept bid: {e}")
            
    def check_job_status(self):
        """Check job status and delivery"""
        if not self.current_job_id:
            print("❌ No active job")
            return
            
        print(f"📊 Checking job {self.current_job_id} status...")
        
        try:
            # Get job state from contract
            job_state, bids = self.contracts.order_book.functions.getJob(self.current_job_id).call()
            
            # JobState: (id, poster, description, metadataURI, deadline, status, acceptedBid, tags)
            status = job_state[5]  # Status enum
            accepted_bid = job_state[6]
            
            status_names = ["Open", "InProgress", "Completed", "Cancelled"]
            status_name = status_names[status] if status < len(status_names) else "Unknown"
            
            print(f"   Status: {status_name}")
            print(f"   Accepted Bid: {accepted_bid}")
            
            if status == 2:  # Completed
                print("\n✅ Job completed!")
                print("📥 Fetching delivery from NeoFS...")
                
                # In production, worker would have uploaded delivery to NeoFS
                # and submitted deliveryURI hash to contract
                print("   (Delivery retrieval to be implemented)")
                
        except Exception as e:
            print(f"❌ Failed to check status: {e}")
            
    def get_help_message(self) -> str:
        """Get help message"""
        return """
🤖 Butler Agent Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Available Tasks:
  • TikTok Scraping - "scrape TikTok user @username"
  • Web Scraping - "scrape website https://example.com"
  • Data Analysis - "analyze data from [source]"
  • Content Generation - "generate [type] content about [topic]"

💬 Commands:
  • status - Check current job status
  • help/? - Show this help message
  • exit/quit/bye - Exit the Butler

💡 Tips:
  • Just tell me what you want in natural language
  • I'll ask follow-up questions to get all details
  • Review and confirm before posting to marketplace
  • Track your job with 'status' command
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def run(self):
        """Main CLI loop"""
        if not self.initialize():
            print("❌ Initialization failed. Exiting.")
            return
            
        print("👋 Hi! I'm your Butler agent.")
        print("   I can help you post jobs and hire agents from the marketplace.")
        print("   Type 'help' for available commands.\n")
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                    
                self.conversation_history.append({"role": "user", "content": user_input})
                
                # Process input
                response = self.process_user_input(user_input)
                
                # Handle action
                if response["action"] == "exit":
                    print(f"\nButler: {response['message']}")
                    break
                    
                elif response["action"] == "help":
                    print(response["message"])
                    
                elif response["action"] == "status":
                    self.check_job_status()
                    
                elif response["action"] == "question":
                    print(f"\nButler: {response['message']}")
                    
                elif response["action"] == "confirm":
                    print(f"\nButler: {response['message']}")
                    
                    # Wait for yes/no
                    confirm = input("\nYou: ").strip().lower()
                    
                    if confirm in ['yes', 'y', 'sure', 'ok', 'yeah']:
                        # Post job
                        result = self.post_job_with_neofs()
                        
                        if result["success"]:
                            print(f"\n✅ Job posted successfully!")
                            
                            # Wait for bids
                            bids = self.wait_for_bids(timeout=10)
                            
                            if bids:
                                self.display_bids(bids)
                                
                                # Ask if user wants to accept
                                print(f"\nWould you like to accept the recommended bid? (yes/no)")
                                accept = input("You: ").strip().lower()
                                
                                if accept in ['yes', 'y', 'sure', 'ok', 'yeah']:
                                    self.accept_bid_and_track()
                                else:
                                    print("\nButler: Okay, you can accept a bid later or wait for more bids.")
                            else:
                                print("\n⚠️  No bids received. Agents might be offline.")
                                print("   Your job is still open on the marketplace.")
                                print(f"   Job ID: {self.current_job_id}")
                        else:
                            print(f"\n❌ Failed to post job: {result.get('error')}")
                    else:
                        print("\nButler: Okay, let's start over. What would you like to do?")
                        self.current_tool = None
                        self.current_slots = {}
                        
            except KeyboardInterrupt:
                print("\n\nButler: Goodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Butler: Sorry, something went wrong. Let's try again.")


def main():
    """Entry point"""
    butler = ButlerCLI()
    butler.run()


if __name__ == "__main__":
    main()
