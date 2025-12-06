"""
Utility to accept a bid on a job using the agent's configured private key.
Meant to be run manually to trigger BidAccepted (and downstream ElevenLabs call).
"""

import os
from dotenv import load_dotenv
from web3 import Web3
from agents.src.shared.contracts import load_abi

load_dotenv()


def accept_bid(job_id: int, bid_id: int, response_uri: str = "archive://response") -> str:
    private_key = os.getenv("TIKTOK_PRIVATE_KEY") or os.getenv("NEOX_PRIVATE_KEY")
    if not private_key:
        raise ValueError("TIKTOK_PRIVATE_KEY or NEOX_PRIVATE_KEY not set")

    rpc_url = os.getenv("NEOX_RPC_URL", "https://testnet.rpc.banelabs.org")
    orderbook_addr = os.getenv("ORDERBOOK_ADDRESS")
    if not orderbook_addr:
        raise ValueError("ORDERBOOK_ADDRESS not set")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = w3.eth.account.from_key(private_key)

    abi = load_abi("OrderBook")
    ob = w3.eth.contract(address=Web3.to_checksum_address(orderbook_addr), abi=abi)

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = ob.functions.acceptBid(job_id, bid_id, response_uri).build_transaction(
        {
            "from": acct.address,
            "nonce": nonce,
            "gas": 800_000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, private_key)
    raw_tx = signed.raw_transaction if hasattr(signed, "raw_transaction") else signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    rec = w3.eth.wait_for_transaction_receipt(tx_hash)
    if rec.status != 1:
        raise RuntimeError(f"Transaction failed: {tx_hash.hex()}")
    return tx_hash.hex()


if __name__ == "__main__":
    h = accept_bid(14, 7, "archive://response/bid-7-job-14")
    print("accepted bid tx:", h)

