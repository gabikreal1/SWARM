"""
Blockchain Event Listener for Archive Agents

Watches for contract events like JobPosted, BidAccepted, etc.
Uses WebSocket for real-time updates with polling fallback.
"""

import os
import json
import asyncio
import logging
from typing import Callable, Awaitable, Optional, Any
from dataclasses import dataclass
from enum import Enum

from web3 import Web3, AsyncWeb3
from web3.contract import Contract

from .config import get_network, get_contract_addresses
from .contracts import load_abi

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Contract event types we care about"""
    JOB_POSTED = "JobPosted"
    BID_PLACED = "BidPlaced"
    BID_ACCEPTED = "BidAccepted"
    DELIVERY_SUBMITTED = "DeliverySubmitted"
    DELIVERY_APPROVED = "DeliveryApproved"
    JOB_CANCELLED = "JobCancelled"
    AGENT_REGISTERED = "AgentRegistered"


@dataclass
class JobPostedEvent:
    """Parsed JobPosted event"""
    job_id: int
    client: str
    job_type: int
    budget: int
    deadline: int
    description: str
    block_number: int
    tx_hash: str


@dataclass
class BidPlacedEvent:
    """Parsed BidPlaced event"""
    job_id: int
    bid_id: int
    bidder: str
    amount: int
    estimated_time: int
    block_number: int
    tx_hash: str


@dataclass
class BidAcceptedEvent:
    """Parsed BidAccepted event"""
    job_id: int
    bid_id: int
    worker: str
    amount: int
    block_number: int
    tx_hash: str


@dataclass
class DeliverySubmittedEvent:
    """Parsed DeliverySubmitted event"""
    job_id: int
    worker: str
    result_uri: str
    timestamp: int
    block_number: int
    tx_hash: str


# Aliases for convenience
BidSubmittedEvent = BidPlacedEvent


EventCallback = Callable[[Any], Awaitable[None]]


class EventListener:
    """
    Async event listener for Archive Protocol contracts.
    
    Watches for events and triggers callbacks for each agent type.
    """
    
    def __init__(
        self,
        poll_interval: int = 3,
        confirmations: int = 1
    ):
        """
        Initialize event listener.
        
        Args:
            poll_interval: Seconds between polls
            confirmations: Block confirmations required
        """
        self.network = get_network()
        self.addresses = get_contract_addresses()
        self.poll_interval = poll_interval
        self.confirmations = confirmations
        
        # Callbacks per event type
        self._callbacks: dict[EventType, list[EventCallback]] = {
            et: [] for et in EventType
        }
        
        # State
        self._running = False
        self._last_block: Optional[int] = None
        self._w3: Optional[Web3] = None
        self._order_book: Optional[Contract] = None
        self._agent_registry: Optional[Contract] = None
    
    def _setup_contracts(self):
        """Initialize Web3 and contract instances"""
        self._w3 = Web3(Web3.HTTPProvider(self.network.rpc_url))
        
        if self.addresses.order_book:
            order_book_abi = load_abi("OrderBook")
            self._order_book = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.addresses.order_book),
                abi=order_book_abi
            )
        
        if self.addresses.agent_registry:
            agent_registry_abi = load_abi("AgentRegistry")
            self._agent_registry = self._w3.eth.contract(
                address=Web3.to_checksum_address(self.addresses.agent_registry),
                abi=agent_registry_abi
            )
    
    def on_event(self, event_type: EventType, callback: EventCallback):
        """
        Register a callback for an event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event occurs
        """
        self._callbacks[event_type].append(callback)
        logger.debug(f"Registered callback for {event_type.value}")
    
    def on_job_posted(self, callback: Callable[[JobPostedEvent], Awaitable[None]]):
        """Register callback for JobPosted events"""
        self.on_event(EventType.JOB_POSTED, callback)
    
    def on_bid_placed(self, callback: Callable[[BidPlacedEvent], Awaitable[None]]):
        """Register callback for BidPlaced events"""
        self.on_event(EventType.BID_PLACED, callback)
    
    # Alias for on_bid_placed
    on_bid_submitted = on_bid_placed
    
    def on_bid_accepted(self, callback: Callable[[BidAcceptedEvent], Awaitable[None]]):
        """Register callback for BidAccepted events"""
        self.on_event(EventType.BID_ACCEPTED, callback)
    
    def on_delivery_submitted(self, callback: Callable[[DeliverySubmittedEvent], Awaitable[None]]):
        """Register callback for DeliverySubmitted events"""
        self.on_event(EventType.DELIVERY_SUBMITTED, callback)
    
    async def _process_job_posted(self, event: dict):
        """Parse and dispatch JobPosted event"""
        args = event['args']
        parsed = JobPostedEvent(
            job_id=args.get('jobId', args.get('id', 0)),
            client=args.get('client', args.get('poster', '')),
            job_type=args.get('jobType', 0),
            budget=args.get('budget', 0),
            deadline=args.get('deadline', 0),
            description=args.get('description', ''),
            block_number=event['blockNumber'],
            tx_hash=event['transactionHash'].hex() if event['transactionHash'] else ''
        )
        logger.info("JobPosted evt job_id=%s type=%s budget=%s deadline=%s desc=%s tx=%s",
                    parsed.job_id, parsed.job_type, parsed.budget, parsed.deadline, parsed.description, parsed.tx_hash)
        for callback in self._callbacks[EventType.JOB_POSTED]:
            try:
                await callback(parsed)
            except Exception as e:
                logger.error(f"Error in JobPosted callback: {e}")
    
    async def _process_bid_placed(self, event: dict):
        """Parse and dispatch BidPlaced event"""
        args = event['args']
        parsed = BidPlacedEvent(
            job_id=args.get('jobId', 0),
            bid_id=args.get('bidId', 0),
            bidder=args.get('bidder', ''),
            amount=args.get('amount', 0),
            estimated_time=args.get('estimatedTime', 0),
            block_number=event['blockNumber'],
            tx_hash=event['transactionHash'].hex() if event['transactionHash'] else ''
        )
        logger.info("BidPlaced evt job_id=%s bid_id=%s bidder=%s amount=%s tx=%s",
                    parsed.job_id, parsed.bid_id, parsed.bidder, parsed.amount, parsed.tx_hash)
        for callback in self._callbacks[EventType.BID_PLACED]:
            try:
                await callback(parsed)
            except Exception as e:
                logger.error(f"Error in BidPlaced callback: {e}")
    
    async def _process_bid_accepted(self, event: dict):
        """Parse and dispatch BidAccepted event"""
        args = event['args']
        parsed = BidAcceptedEvent(
            job_id=args.get('jobId', 0),
            bid_id=args.get('bidId', 0),
            worker=args.get('worker', args.get('bidder', '')),
            amount=args.get('amount', 0),
            block_number=event['blockNumber'],
            tx_hash=event['transactionHash'].hex() if event['transactionHash'] else ''
        )
        logger.info("BidAccepted evt job_id=%s bid_id=%s worker=%s amount=%s tx=%s",
                    parsed.job_id, parsed.bid_id, parsed.worker, parsed.amount, parsed.tx_hash)
        for callback in self._callbacks[EventType.BID_ACCEPTED]:
            try:
                await callback(parsed)
            except Exception as e:
                logger.error(f"Error in BidAccepted callback: {e}")
    
    async def _process_delivery_submitted(self, event: dict):
        """Parse and dispatch DeliverySubmitted event"""
        args = event['args']
        parsed = DeliverySubmittedEvent(
            job_id=args.get('jobId', 0),
            worker=args.get('worker', ''),
            result_uri=args.get('resultUri', args.get('deliveryUri', '')),
            timestamp=args.get('timestamp', 0),
            block_number=event['blockNumber'],
            tx_hash=event['transactionHash'].hex() if event['transactionHash'] else ''
        )
        logger.info("DeliverySubmitted evt job_id=%s worker=%s result=%s tx=%s",
                    parsed.job_id, parsed.worker, parsed.result_uri, parsed.tx_hash)
        for callback in self._callbacks[EventType.DELIVERY_SUBMITTED]:
            try:
                await callback(parsed)
            except Exception as e:
                logger.error(f"Error in DeliverySubmitted callback: {e}")

    async def _poll_events(self):
        """Poll for new events"""
        if not self._w3 or not self._order_book:
            return
        
        try:
            current_block = self._w3.eth.block_number
            safe_block = current_block - self.confirmations
            
            if self._last_block is None:
                self._last_block = safe_block - 1
            
            if safe_block <= self._last_block:
                return
            
            from_block = self._last_block + 1
            to_block = safe_block
            
            logger.debug(f"Polling blocks {from_block} to {to_block}")
            
            # Get JobPosted events
            if self._callbacks[EventType.JOB_POSTED]:
                try:
                    events = self._order_book.events.JobPosted.get_logs(
                        from_block=from_block,
                        to_block=to_block
                    )
                    for event in events:
                        await self._process_job_posted(event)
                except Exception as e:
                    logger.debug(f"No JobPosted events or error: {e}")
            
            # Get BidPlaced events
            if self._callbacks[EventType.BID_PLACED]:
                try:
                    events = self._order_book.events.BidPlaced.get_logs(
                        from_block=from_block,
                        to_block=to_block
                    )
                    for event in events:
                        await self._process_bid_placed(event)
                except Exception as e:
                    logger.debug(f"No BidPlaced events or error: {e}")
            
            # Get BidAccepted events
            if self._callbacks[EventType.BID_ACCEPTED]:
                try:
                    events = self._order_book.events.BidAccepted.get_logs(
                        from_block=from_block,
                        to_block=to_block
                    )
                    for event in events:
                        await self._process_bid_accepted(event)
                except Exception as e:
                    logger.debug(f"No BidAccepted events or error: {e}")
            
            # Get DeliverySubmitted events
            if self._callbacks[EventType.DELIVERY_SUBMITTED]:
                try:
                    events = self._order_book.events.DeliverySubmitted.get_logs(
                        from_block=from_block,
                        to_block=to_block
                    )
                    for event in events:
                        await self._process_delivery_submitted(event)
                except Exception as e:
                    logger.debug(f"No DeliverySubmitted events or error: {e}")
            
            self._last_block = to_block
            
        except Exception as e:
            logger.error(f"Error polling events: {e}")
    
    async def start(self):
        """Start the event listener"""
        logger.info("Starting event listener...")
        self._setup_contracts()
        self._running = True
        
        while self._running:
            await self._poll_events()
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the event listener"""
        logger.info("Stopping event listener...")
        self._running = False

    async def catch_up(self, blocks_back: int = 20):
        """Process recent events immediately (e.g., jobs posted before agent startup)."""
        if not self._w3 or not self._order_book:
            self._setup_contracts()
        try:
            current_block = self._w3.eth.block_number
            safe_block = current_block - self.confirmations
            if safe_block <= 0:
                return
            from_block = max(0, safe_block - blocks_back)
            to_block = safe_block
            logger.info("Catching up events from block %s to %s", from_block, to_block)

            if self._callbacks[EventType.JOB_POSTED]:
                events = self._order_book.events.JobPosted.get_logs(
                    from_block=from_block,
                    to_block=to_block,
                )
                for event in events:
                    await self._process_job_posted(event)

            if self._callbacks[EventType.BID_PLACED]:
                events = self._order_book.events.BidPlaced.get_logs(
                    from_block=from_block,
                    to_block=to_block,
                )
                for event in events:
                    await self._process_bid_placed(event)

            if self._callbacks[EventType.BID_ACCEPTED]:
                events = self._order_book.events.BidAccepted.get_logs(
                    from_block=from_block,
                    to_block=to_block,
                )
                for event in events:
                    await self._process_bid_accepted(event)

            if self._callbacks[EventType.DELIVERY_SUBMITTED]:
                events = self._order_book.events.DeliverySubmitted.get_logs(
                    from_block=from_block,
                    to_block=to_block,
                )
                for event in events:
                    await self._process_delivery_submitted(event)

            self._last_block = to_block
        except Exception as e:
            logger.error("Catch-up failed: %s", e)
    
    async def run_once(self):
        """Poll events once (for testing)"""
        self._setup_contracts()
        await self._poll_events()


def create_event_listener(poll_interval: int = 3) -> EventListener:
    """Create a new event listener instance"""
    return EventListener(poll_interval=poll_interval)
