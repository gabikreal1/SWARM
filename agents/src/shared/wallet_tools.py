"""
Wallet Tools for Archive Agents

SpoonOS tools for wallet operations that all agents share.
"""

import json
from typing import Optional
from decimal import Decimal

from pydantic import Field
from spoon_ai.tools.base import BaseTool

from .wallet import AgentWallet


class GetWalletBalanceTool(BaseTool):
    """Tool to check wallet balance"""
    
    name: str = "get_wallet_balance"
    description: str = """
    Check the current balance of the agent's wallet.
    Returns native token (GAS) and USDC balances.
    """
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Wallet is injected at runtime
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        try:
            balance = self._wallet.get_balance()
            return json.dumps({
                "success": True,
                "address": self._wallet.address,
                "native_balance": str(balance.native),
                "native_symbol": "GAS",
                "usdc_balance": str(balance.usdc),
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class GetWalletAddressTool(BaseTool):
    """Tool to get wallet address"""
    
    name: str = "get_wallet_address"
    description: str = """
    Get the agent's wallet address.
    """
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        return json.dumps({
            "success": True,
            "address": self._wallet.address
        })


class TransferNativeTool(BaseTool):
    """Tool to transfer native tokens"""
    
    name: str = "transfer_native"
    description: str = """
    Transfer native tokens (GAS) to another address.
    Use with caution - this spends real funds.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "to_address": {
                "type": "string",
                "description": "Recipient wallet address"
            },
            "amount": {
                "type": "string",
                "description": "Amount in GAS (e.g., '0.1')"
            }
        },
        "required": ["to_address", "amount"]
    }
    
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self, to_address: str, amount: str) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        try:
            result = self._wallet.transfer_native(to_address, Decimal(amount))
            return json.dumps(result.to_dict(), indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class TransferUSDCTool(BaseTool):
    """Tool to transfer USDC tokens"""
    
    name: str = "transfer_usdc"
    description: str = """
    Transfer USDC tokens to another address.
    Use with caution - this spends real funds.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "to_address": {
                "type": "string",
                "description": "Recipient wallet address"
            },
            "amount": {
                "type": "string",
                "description": "Amount in USDC (e.g., '10.50')"
            }
        },
        "required": ["to_address", "amount"]
    }
    
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self, to_address: str, amount: str) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        try:
            result = self._wallet.transfer_usdc(to_address, Decimal(amount))
            return json.dumps(result.to_dict(), indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class ApproveUSDCTool(BaseTool):
    """Tool to approve USDC spending"""
    
    name: str = "approve_usdc"
    description: str = """
    Approve a contract to spend USDC on behalf of the agent.
    Required before interacting with escrow contracts.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "spender_address": {
                "type": "string",
                "description": "Contract address to approve"
            },
            "amount": {
                "type": "string",
                "description": "Amount to approve in USDC (use 'unlimited' for max)"
            }
        },
        "required": ["spender_address", "amount"]
    }
    
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self, spender_address: str, amount: str) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        try:
            if amount.lower() == "unlimited":
                decimal_amount = Decimal('inf')
            else:
                decimal_amount = Decimal(amount)
            
            result = self._wallet.approve_usdc(spender_address, decimal_amount)
            return json.dumps(result.to_dict(), indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class SignMessageTool(BaseTool):
    """Tool to sign a message with wallet"""
    
    name: str = "sign_message"
    description: str = """
    Sign a message with the agent's wallet private key.
    Useful for authentication and A2A protocol.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to sign"
            }
        },
        "required": ["message"]
    }
    
    _wallet: Optional[AgentWallet] = None
    
    def set_wallet(self, wallet: AgentWallet):
        self._wallet = wallet
    
    async def execute(self, message: str) -> str:
        if not self._wallet:
            return json.dumps({"error": "Wallet not configured"})
        
        try:
            signature = self._wallet.sign_message(message)
            return json.dumps({
                "success": True,
                "message": message,
                "signature": signature,
                "signer": self._wallet.address
            }, indent=2)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


def create_wallet_tools(wallet: Optional[AgentWallet] = None) -> list[BaseTool]:
    """
    Create all wallet tools with optional wallet injection.
    
    Args:
        wallet: AgentWallet to inject into tools
    
    Returns:
        List of wallet tools
    """
    tools = [
        GetWalletBalanceTool(),
        GetWalletAddressTool(),
        TransferNativeTool(),
        TransferUSDCTool(),
        ApproveUSDCTool(),
        SignMessageTool(),
    ]
    
    if wallet:
        for tool in tools:
            tool.set_wallet(wallet)
    
    return tools
