"""
Wallet Management for Archive Agents

Each agent has its own wallet for:
- Signing transactions
- Managing funds
- Interacting with contracts
"""

import os
import json
from typing import Optional
from dataclasses import dataclass, field
from decimal import Decimal

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from .config import get_network, get_contract_addresses


@dataclass
class WalletBalance:
    """Wallet balance information"""
    native: Decimal  # GAS balance
    usdc: Decimal    # USDC balance
    
    def to_dict(self) -> dict:
        return {
            "native": str(self.native),
            "usdc": str(self.usdc),
        }


@dataclass
class TransactionResult:
    """Result of a transaction"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    gas_used: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "error": self.error,
            "gas_used": self.gas_used,
        }


class AgentWallet:
    """
    Wallet wrapper for an agent.
    
    Provides high-level methods for:
    - Balance checking
    - Token transfers
    - Contract interactions
    - Transaction signing
    """
    
    def __init__(self, private_key: str, agent_name: str = "agent"):
        """
        Initialize wallet with private key.
        
        Args:
            private_key: Hex-encoded private key (with or without 0x prefix)
            agent_name: Name of the agent for logging
        """
        self.agent_name = agent_name
        self.network = get_network()
        self.addresses = get_contract_addresses()
        
        # Create Web3 instance
        self.w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
        
        # Create account from private key
        if not private_key.startswith("0x"):
            private_key = f"0x{private_key}"
        self.account: LocalAccount = Account.from_key(private_key)
        self.w3.eth.default_account = self.account.address
        
        # Load USDC ABI for token operations
        self._usdc_abi = self._load_erc20_abi()
    
    @property
    def address(self) -> str:
        """Get wallet address"""
        return self.account.address
    
    @property
    def private_key(self) -> str:
        """Get private key (be careful with this!)"""
        return self.account.key.hex()
    
    def _load_erc20_abi(self) -> list:
        """Load minimal ERC20 ABI for token operations"""
        return [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]
    
    def get_balance(self) -> WalletBalance:
        """Get current wallet balances"""
        # Native balance (GAS)
        native_wei = self.w3.eth.get_balance(self.address)
        native = Decimal(self.w3.from_wei(native_wei, 'ether'))
        
        # USDC balance
        usdc = Decimal(0)
        if self.addresses.usdc:
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.addresses.usdc),
                abi=self._usdc_abi
            )
            usdc_raw = usdc_contract.functions.balanceOf(self.address).call()
            # USDC has 6 decimals
            usdc = Decimal(usdc_raw) / Decimal(10 ** 6)
        
        return WalletBalance(native=native, usdc=usdc)
    
    def get_native_balance(self) -> Decimal:
        """Get native token balance in ether"""
        wei = self.w3.eth.get_balance(self.address)
        return Decimal(self.w3.from_wei(wei, 'ether'))
    
    def get_usdc_balance(self) -> Decimal:
        """Get USDC balance"""
        if not self.addresses.usdc:
            return Decimal(0)
        
        usdc_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.addresses.usdc),
            abi=self._usdc_abi
        )
        raw = usdc_contract.functions.balanceOf(self.address).call()
        return Decimal(raw) / Decimal(10 ** 6)
    
    def transfer_native(self, to: str, amount_ether: Decimal) -> TransactionResult:
        """
        Transfer native tokens (GAS).
        
        Args:
            to: Recipient address
            amount_ether: Amount in ether
        """
        try:
            tx = {
                'from': self.address,
                'to': Web3.to_checksum_address(to),
                'value': self.w3.to_wei(float(amount_ether), 'ether'),
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.network.chain_id,
            }
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                gas_used=receipt['gasUsed']
            )
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def transfer_usdc(self, to: str, amount: Decimal) -> TransactionResult:
        """
        Transfer USDC tokens.
        
        Args:
            to: Recipient address
            amount: Amount in USDC (not raw units)
        """
        if not self.addresses.usdc:
            return TransactionResult(success=False, error="USDC address not configured")
        
        try:
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.addresses.usdc),
                abi=self._usdc_abi
            )
            
            # Convert to raw units (6 decimals)
            raw_amount = int(amount * 10 ** 6)
            
            tx = usdc_contract.functions.transfer(
                Web3.to_checksum_address(to),
                raw_amount
            ).build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.network.chain_id,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                gas_used=receipt['gasUsed']
            )
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def approve_usdc(self, spender: str, amount: Decimal) -> TransactionResult:
        """
        Approve USDC spending for a contract.
        
        Args:
            spender: Contract address to approve
            amount: Amount to approve (use Decimal('inf') for unlimited)
        """
        if not self.addresses.usdc:
            return TransactionResult(success=False, error="USDC address not configured")
        
        try:
            usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.addresses.usdc),
                abi=self._usdc_abi
            )
            
            # Max uint256 for unlimited approval, otherwise convert
            if amount == Decimal('inf'):
                raw_amount = 2**256 - 1
            else:
                raw_amount = int(amount * 10 ** 6)
            
            tx = usdc_contract.functions.approve(
                Web3.to_checksum_address(spender),
                raw_amount
            ).build_transaction({
                'from': self.address,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.network.chain_id,
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return TransactionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                gas_used=receipt['gasUsed']
            )
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def sign_message(self, message: str) -> str:
        """Sign a message with the wallet's private key"""
        from eth_account.messages import encode_defunct
        
        msg = encode_defunct(text=message)
        signed = self.w3.eth.account.sign_message(msg, self.account.key)
        return signed.signature.hex()
    
    def get_nonce(self) -> int:
        """Get current nonce for the wallet"""
        return self.w3.eth.get_transaction_count(self.address)
    
    def estimate_gas(self, to: str, data: bytes = b'', value: int = 0) -> int:
        """Estimate gas for a transaction"""
        return self.w3.eth.estimate_gas({
            'from': self.address,
            'to': Web3.to_checksum_address(to),
            'data': data,
            'value': value
        })
    
    def __repr__(self) -> str:
        return f"AgentWallet({self.agent_name}, {self.address[:10]}...)"


def create_wallet_from_env(agent_type: str) -> Optional[AgentWallet]:
    """
    Create a wallet from environment variable.
    
    Args:
        agent_type: One of 'manager', 'scraper', 'caller'
    
    Returns:
        AgentWallet or None if key not found
    """
    key_name = f"{agent_type.upper()}_PRIVATE_KEY"
    private_key = os.getenv(key_name)
    
    if not private_key:
        return None
    
    return AgentWallet(private_key, agent_type)


def generate_new_wallet() -> tuple[str, str]:
    """
    Generate a new random wallet.
    
    Returns:
        Tuple of (address, private_key)
    """
    account = Account.create()
    return account.address, account.key.hex()
