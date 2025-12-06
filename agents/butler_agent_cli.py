"""
Butler CLI - Interactive Command Line Interface

Real implementation using the Butler Agent with:
- Natural language conversation
- RAG-powered Q&A
- Slot filling for job posting
- Bid evaluation and selection
- Job monitoring and delivery
"""

import os
import sys
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

# Add SWARM root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose logs from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("web3").setLevel(logging.WARNING)

load_dotenv()

try:
    from agents.src.butler.agent import create_butler_agent
    BUTLER_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Butler Agent not available: {e}")
    print("   Falling back to basic CLI...")
    BUTLER_AGENT_AVAILABLE = False


class ButlerCLI:
    """Interactive CLI for Butler Agent"""
    
    def __init__(self):
        self.butler = None
        self.user_id = "cli_user"
        
    async def initialize(self):
        """Initialize Butler Agent"""
        print("🤖 Archive Protocol - Butler AI")
        print("=" * 60)
        
        # Check environment
        private_key = os.getenv("NEOX_PRIVATE_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not private_key:
            print("❌ NEOX_PRIVATE_KEY not found in .env")
            return False
        
        if not openai_key:
            print("❌ OPENAI_API_KEY not found in .env")
            return False
        
        if not BUTLER_AGENT_AVAILABLE:
            print("❌ Butler Agent dependencies not available")
            print("   Install: pip install spoon-ai")
            return False
        
        try:
            print("🔗 Initializing Butler Agent...")
            self.butler = create_butler_agent(
                private_key=private_key,
                openai_api_key=openai_key,
                model="gpt-4-turbo-preview"
            )
            print("✅ Butler Agent ready!")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Failed to initialize Butler: {e}")
            return False
        
        print("=" * 60)
        print()
        return True
    
    def print_help(self):
        """Print help message"""
        help_text = """
🤖 Butler AI - Commands & Capabilities
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 CONVERSATION:
  Just talk naturally! The Butler understands:
  • Questions about restaurants, services, etc.
  • Requests to scrape data
  • Job status checks
  • Help with bids and deliveries

📝 AVAILABLE JOBS:
  • TikTok Scraping - "scrape TikTok user @username"
  • Web Scraping - "scrape website https://example.com"
  • Data Analysis - "analyze data from [source]"
  • Content Generation - "create content about [topic]"

💡 EXAMPLE CONVERSATIONS:

  You: "I need to scrape 100 TikTok posts from @elonmusk"
  Butler: "I'll need the username and post count..."
  [Collects details, posts job, shows bids]
  
  You: "What are the best restaurants in Moscow?"
  Butler: [Searches knowledge base and provides answer]
  
  You: "Is my job done yet?"
  Butler: [Checks status and reports back]

🎯 SPECIAL COMMANDS:
  • help or ? - Show this help
  • status - Check current job status
  • exit, quit, bye - Exit Butler

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        print(help_text)
    
    async def run(self):
        """Main CLI loop"""
        if not await self.initialize():
            print("❌ Initialization failed. Exiting.")
            return
        
        print("👋 Hi! I'm your Butler AI assistant.")
        print("   I can answer questions, post jobs, and manage tasks.")
        print("   Type 'help' for more info or just start chatting!\n")
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nButler: Goodbye! Have a great day! 👋")
                    break
                
                if user_input.lower() in ['help', '?']:
                    self.print_help()
                    continue
                
                if user_input.lower() == 'status':
                    if self.butler.current_job_id:
                        print("\nButler: Let me check your job status...")
                        status = await self.butler.check_status()
                        print(f"\nJob Status:\n{status}\n")
                    else:
                        print("\nButler: You don't have any active jobs yet.\n")
                    continue
                
                # Chat with Butler Agent
                print("\nButler: ", end="", flush=True)
                
                # Get response (this may take a moment as tools are called)
                response = await self.butler.chat(user_input, self.user_id)
                
                print(f"{response}\n")
                
            except KeyboardInterrupt:
                print("\n\nButler: Goodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.exception("CLI error")
                print("Butler: Sorry, something went wrong. Let's try again.\n")


async def main():
    """Entry point"""
    cli = ButlerCLI()
    await cli.run()


if __name__ == "__main__":
    # Run async CLI
    asyncio.run(main())
