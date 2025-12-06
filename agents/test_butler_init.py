
import sys
import os
import asyncio
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv()

async def test_init():
    print("Testing Butler Agent initialization...")
    try:
        from src.butler.agent import ButlerAgent
        agent = ButlerAgent()
        print("Butler Agent initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize Butler Agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_init())
