"""
Contract ABI Verification Test

Run this to verify all contract interactions match the deployed ABIs.
"""
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.src.shared.contracts import get_contracts, load_abi

load_dotenv()

def verify_abis():
    """Verify all function signatures match the ABIs"""
    
    print("🔍 Verifying Contract ABIs...\n")
    
    # Load ABIs
    order_book_abi = load_abi("OrderBook")
    escrow_abi = load_abi("Escrow")
    usdc_abi = load_abi("MockUSDC")
    
    # Extract function signatures
    functions = {
        "OrderBook": {},
        "Escrow": {},
        "MockUSDC": {}
    }
    
    for item in order_book_abi:
        if item.get("type") == "function":
            name = item["name"]
            inputs = [inp["type"] for inp in item.get("inputs", [])]
            functions["OrderBook"][name] = inputs
    
    for item in escrow_abi:
        if item.get("type") == "function":
            name = item["name"]
            inputs = [inp["type"] for inp in item.get("inputs", [])]
            functions["Escrow"][name] = inputs
    
    for item in usdc_abi:
        if item.get("type") == "function":
            name = item["name"]
            inputs = [inp["type"] for inp in item.get("inputs", [])]
            functions["MockUSDC"][name] = inputs
    
    # Verify critical functions
    print("📋 OrderBook Functions:")
    print(f"  postJob: {functions['OrderBook'].get('postJob')}")
    print(f"    Expected: ['string', 'string', 'string[]', 'uint64']")
    print(f"    ✅ Match" if functions['OrderBook'].get('postJob') == ['string', 'string', 'string[]', 'uint64'] else "    ❌ MISMATCH")
    
    print(f"\n  placeBid: {functions['OrderBook'].get('placeBid')}")
    print(f"    Expected: ['uint256', 'uint256', 'uint64', 'string']")
    print(f"    ✅ Match" if functions['OrderBook'].get('placeBid') == ['uint256', 'uint256', 'uint64', 'string'] else "    ❌ MISMATCH")
    
    print(f"\n  acceptBid: {functions['OrderBook'].get('acceptBid')}")
    print(f"    Expected: ['uint256', 'uint256', 'string']")
    print(f"    ✅ Match" if functions['OrderBook'].get('acceptBid') == ['uint256', 'uint256', 'string'] else "    ❌ MISMATCH")
    
    print(f"\n  getJob: {functions['OrderBook'].get('getJob')}")
    print(f"    Expected: ['uint256']")
    print(f"    ✅ Match" if functions['OrderBook'].get('getJob') == ['uint256'] else "    ❌ MISMATCH")
    
    print(f"\n📋 MockUSDC Functions:")
    print(f"  approve: {functions['MockUSDC'].get('approve')}")
    print(f"    Expected: ['address', 'uint256']")
    print(f"    ✅ Match" if functions['MockUSDC'].get('approve') == ['address', 'uint256'] else "    ❌ MISMATCH")
    
    print(f"\n  mint: {functions['MockUSDC'].get('mint')}")
    print(f"    Expected: ['address', 'uint256']")
    print(f"    ✅ Match" if functions['MockUSDC'].get('mint') == ['address', 'uint256'] else "    ❌ MISMATCH")
    
    # Try connecting to contracts
    print("\n🔗 Testing Contract Connection...")
    try:
        private_key = os.getenv("NEOX_PRIVATE_KEY")
        if not private_key:
            print("⚠️  NEOX_PRIVATE_KEY not set, skipping connection test")
            return
        
        contracts = get_contracts(private_key)
        print(f"✅ Connected to OrderBook: {contracts.order_book.address}")
        print(f"✅ Connected to Escrow: {contracts.escrow.address}")
        print(f"✅ Connected to USDC: {contracts.usdc.address}")
        
        # Test a read-only call
        print("\n📞 Testing Read Calls...")
        try:
            balance = contracts.usdc.functions.balanceOf(contracts.account.address).call()
            print(f"✅ USDC Balance: {balance / 10**6} USDC")
        except Exception as e:
            print(f"❌ Balance check failed: {e}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    
    print("\n✅ Verification Complete!")

if __name__ == "__main__":
    verify_abis()
