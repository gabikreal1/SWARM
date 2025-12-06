"""
Butler Agent CLI - Quick Start

This is the REAL Butler agent implementation based on the PRD.

Features:
✅ Natural language conversation with OpenAI GPT-4
✅ RAG-powered Q&A (Qdrant + Mem0)
✅ Slot filling for job posting
✅ NeoFS integration for job metadata
✅ Blockchain OrderBook integration
✅ Bid evaluation and selection
✅ Job monitoring and delivery tracking

Architecture:
- src/butler/agent.py - Main Butler agent with ToolCallAgent
- src/butler/tools.py - Butler-specific tools (RAG, slots, job posting)
- butler_agent_cli.py - Interactive CLI interface

This replaces butler_cli.py with a proper agent architecture.
"""

import os
import sys

# Quick environment check
def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment...")
    print()
    
    required_vars = {
        "NEOX_PRIVATE_KEY": "Blockchain private key",
        "OPENAI_API_KEY": "OpenAI API for LLM",
        "NEOFS_CONTAINER_ID": "NeoFS storage container",
        "QDRANT_URL": "Qdrant vector DB (optional)",
        "MEM0_API_KEY": "Mem0 memory service (optional)"
    }
    
    from dotenv import load_dotenv
    load_dotenv()
    
    missing = []
    optional_missing = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            print(f"✅ {var}: {masked}")
        else:
            if "optional" in description.lower():
                optional_missing.append(f"⚠️  {var}: Not set ({description})")
            else:
                missing.append(f"❌ {var}: Missing ({description})")
    
    print()
    
    if missing:
        for msg in missing:
            print(msg)
        print()
        print("Please set required environment variables in .env file")
        return False
    
    if optional_missing:
        for msg in optional_missing:
            print(msg)
        print()
        print("Optional features will be disabled")
    
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("🤖 Archive Protocol - Butler AI Agent")
    print("=" * 70)
    print()
    
    if not check_environment():
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("🚀 Starting Butler CLI...")
    print("=" * 70)
    print()
    
    # Import and run
    try:
        import asyncio
        from butler_agent_cli import main
        
        asyncio.run(main())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print()
        print("Missing dependencies. Install with:")
        print("  pip install spoon-ai openai web3 qdrant-client mem0ai python-dotenv")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
