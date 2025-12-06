"""
Web3 Contract Interactions for Archive Agents

Connects to deployed contracts on NeoX blockchain.
"""

import os
import json
from pathlib import Path
from typing import Optional, Any, Callable
from dataclasses import dataclass

import logging
from web3 import Web3, AsyncWeb3
from web3.contract import Contract, AsyncContract
from eth_account import Account
from eth_account.signers.local import LocalAccount

from .config import get_network, get_contract_addresses, ContractAddresses

logger = logging.getLogger(__name__)


# Load ABIs from contracts directory
def load_abi(contract_name: str) -> list:
    """Load ABI from the contracts integrations folder"""
    abi_path = Path(__file__).parent.parent.parent.parent / "contracts" / "integrations" / "spoon" / "abi" / f"{contract_name}.json"
    if abi_path.exists():
        with open(abi_path, "r") as f:
            data = json.load(f)
            # Handle both direct ABI arrays and wrapped {abi: [...]} objects
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'abi' in data:
                return data['abi']
            else:
                raise ValueError(f"Unexpected ABI format in {abi_path}")
    raise FileNotFoundError(f"ABI not found: {abi_path}")


@dataclass
class ContractInstances:
    """Container for all contract instances"""
    w3: Web3
    account: Optional[LocalAccount]
    order_book: Contract
    escrow: Contract
    job_registry: Contract
    agent_registry: Contract
    reputation_token: Contract
    usdc: Contract
    addresses: ContractAddresses


def get_contracts(private_key: Optional[str] = None) -> ContractInstances:
    """
    Get contract instances for the specified network.
    
    Args:
        private_key: Optional private key for signing transactions
        
    Returns:
        ContractInstances with all contract connections
    """
    network = get_network()
    addresses = get_contract_addresses()
    
    # Validate addresses
    if not addresses.order_book or not addresses.escrow:
        raise ValueError(
            "Contract addresses not configured. "
            "Please deploy contracts first and set environment variables."
        )
    
    # Create Web3 instance
    w3 = Web3(Web3.HTTPProvider(network.rpc_url))
    logger.info("Connecting to RPC %s chain_id=%s", network.rpc_url, network.chain_id)
    
    # Set up account if private key provided
    account = None
    if private_key:
        account = Account.from_key(private_key)
        w3.eth.default_account = account.address
        logger.info("Loaded account %s", account.address)
    
    # Load ABIs
    order_book_abi = load_abi("OrderBook")
    escrow_abi = load_abi("Escrow")
    job_registry_abi = load_abi("JobRegistry")
    agent_registry_abi = load_abi("AgentRegistry")
    reputation_token_abi = load_abi("ReputationToken")
    usdc_abi = load_abi("MockUSDC")
    
    # Create contract instances
    order_book = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.order_book),
        abi=order_book_abi
    )
    escrow = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.escrow),
        abi=escrow_abi
    )
    job_registry = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.job_registry),
        abi=job_registry_abi
    )
    agent_registry = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.agent_registry),
        abi=agent_registry_abi
    )
    reputation_token = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.reputation_token),
        abi=reputation_token_abi
    )
    usdc = w3.eth.contract(
        address=Web3.to_checksum_address(addresses.usdc),
        abi=usdc_abi
    )
    
    return ContractInstances(
        w3=w3,
        account=account,
        order_book=order_book,
        escrow=escrow,
        job_registry=job_registry,
        agent_registry=agent_registry,
        reputation_token=reputation_token,
        usdc=usdc,
        addresses=addresses,
    )


def send_transaction(
    contracts: ContractInstances,
    contract_func: Any,
    *args,
    **kwargs
) -> str:
    """
    Build, sign, and send a transaction.
    
    Returns:
        Transaction hash
    """
    if not contracts.account:
        raise ValueError("No account configured for signing transactions")
    
    logger.info("Sending tx %s args=%s kwargs=%s", getattr(contract_func, "fn_name", ""), args, kwargs)
    
    # Build transaction
    tx = contract_func(*args, **kwargs).build_transaction({
        'from': contracts.account.address,
        'nonce': contracts.w3.eth.get_transaction_count(contracts.account.address),
        'gas': 500000,
        'gasPrice': contracts.w3.eth.gas_price,
    })
    
    # Sign and send
    signed_tx = contracts.w3.eth.account.sign_transaction(tx, contracts.account.key)
    tx_hash = contracts.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    return tx_hash.hex()


def wait_for_receipt(contracts: ContractInstances, tx_hash: str, timeout: int = 120):
    """Wait for transaction receipt"""
    return contracts.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)


# High-level contract operations

def approve_usdc(
    contracts: ContractInstances,
    spender: str,
    amount: int
) -> str:
    """Approve spender to spend USDC"""
    tx_hash = send_transaction(
        contracts,
        contracts.usdc.functions.approve,
        Web3.to_checksum_address(spender),
        amount
    )
    wait_for_receipt(contracts, tx_hash)
    return tx_hash


def post_job(
    contracts: ContractInstances,
    description: str,
    metadata_uri: str,
    tags: list[str],
    deadline: int
) -> int:
    """
    Post a new job to the OrderBook.

    Args:
        description: Human-readable description stored on-chain.
        metadata_uri: Off-chain metadata location (NeoFS/IPFS).
        tags: List of searchable tags to persist in JobRegistry.
        deadline: Optional unix timestamp for completion.
    Returns:
        Job ID
    """
    tx_hash = send_transaction(
        contracts,
        contracts.order_book.functions.postJob,
        description,
        metadata_uri,
        tags,
        deadline
    )
    receipt = wait_for_receipt(contracts, tx_hash)
    
    # Parse JobPosted event
    logs = contracts.order_book.events.JobPosted().process_receipt(receipt)
    if logs:
        return logs[0]['args']['jobId']
    raise ValueError("JobPosted event not found in receipt")


def place_bid(
    contracts: ContractInstances,
    job_id: int,
    amount: int,
    estimated_time: int,
    metadata_uri: str
) -> int:
    """
    Place a bid on a job.
    
    Returns:
        Bid ID
    """
    tx_hash = send_transaction(
        contracts,
        contracts.order_book.functions.placeBid,
        job_id,
        amount,
        estimated_time,
        metadata_uri
    )
    receipt = wait_for_receipt(contracts, tx_hash)
    
    # Parse BidPlaced event
    logs = contracts.order_book.events.BidPlaced().process_receipt(receipt)
    if logs:
        return logs[0]['args']['bidId']
    raise ValueError("BidPlaced event not found in receipt")


def accept_bid(
    contracts: ContractInstances,
    job_id: int,
    bid_id: int,
    response_uri: str
) -> str:
    """Accept a bid and start work"""
    tx_hash = send_transaction(
        contracts,
        contracts.order_book.functions.acceptBid,
        job_id,
        bid_id,
        response_uri
    )
    wait_for_receipt(contracts, tx_hash)
    return tx_hash


def submit_delivery(
    contracts: ContractInstances,
    job_id: int,
    proof_hash: bytes
) -> str:
    """Submit delivery proof"""
    tx_hash = send_transaction(
        contracts,
        contracts.order_book.functions.submitDelivery,
        job_id,
        proof_hash
    )
    wait_for_receipt(contracts, tx_hash)
    return tx_hash


def approve_delivery(contracts: ContractInstances, job_id: int) -> str:
    """Approve delivery and release payment"""
    tx_hash = send_transaction(
        contracts,
        contracts.order_book.functions.approveDelivery,
        job_id
    )
    wait_for_receipt(contracts, tx_hash)
    return tx_hash


def register_agent(
    contracts: ContractInstances,
    name: str,
    endpoint: str,
    capabilities: list[str]
) -> str:
    """Register as an agent"""
    tx_hash = send_transaction(
        contracts,
        contracts.agent_registry.functions.registerAgent,
        name,
        endpoint,
        capabilities
    )
    wait_for_receipt(contracts, tx_hash)
    return tx_hash


def is_agent_active(contracts: ContractInstances, address: str) -> bool:
    """Check if an address is a registered active agent"""
    return contracts.agent_registry.functions.isAgentActive(
        Web3.to_checksum_address(address)
    ).call()


def get_job(contracts: ContractInstances, job_id: int) -> dict:
    """Get job details"""
    return contracts.order_book.functions.getJob(job_id).call()


def get_job_status(contracts: ContractInstances, job_id: int) -> str:
    """
    Get job status as a string.
    Returns one of: OPEN, IN_PROGRESS, DELIVERED, COMPLETED, DISPUTED
    """
    job_data = contracts.order_book.functions.getJob(job_id).call()
    # JobState is first element in the tuple returned by getJob
    status_map = {
        0: "OPEN",
        1: "IN_PROGRESS", 
        2: "DELIVERED",
        3: "COMPLETED",
        4: "DISPUTED"
    }
    return status_map.get(job_data[0], "UNKNOWN")


def get_bids_for_job(contracts: ContractInstances, job_id: int) -> list:
    """Get all bids for a job"""
    # OrderBook.getJob returns (JobState, Bid[])
    result = contracts.order_book.functions.getJob(job_id).call()
    return result[1]  # Return the bids array


def setup_event_listener(
    contracts: ContractInstances,
    event_name: str,
    callback: Callable,
    poll_interval: int = 2
):
    """
    Set up an event listener with polling.
    
    Note: For production, consider using websocket subscriptions.
    """
    contract = contracts.order_book
    event = getattr(contract.events, event_name)
    
    # Get current block as starting point
    from_block = contracts.w3.eth.block_number
    
    import time
    import threading
    
    def poll_events():
        nonlocal from_block
        while True:
            try:
                current_block = contracts.w3.eth.block_number
                if current_block > from_block:
                    events = event.get_logs(fromBlock=from_block + 1, toBlock=current_block)
                    for evt in events:
                        callback(evt)
                    from_block = current_block
            except Exception as e:
                print(f"Error polling events: {e}")
            time.sleep(poll_interval)
    
    thread = threading.Thread(target=poll_events, daemon=True)
    thread.start()
    return thread
