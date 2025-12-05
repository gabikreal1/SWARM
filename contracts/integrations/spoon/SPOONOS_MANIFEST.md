# SpoonOS Integration Manifest

## Overview
This manifest describes how to register and use the NeoxPrep contract suite with SpoonOS.

## Contracts
The following contracts are available for SpoonOS agents to interact with:

### 1. OrderBook
- **Purpose:** Main marketplace contract for posting jobs, accepting bids, and coordinating delivery.
- **Address (Arc 5042002):** `0x36fac95295767593478e332Ab9793955b3e0B111`
- **Key Functions:**
  - `postJob(jobMetadata, bidAmount, deliveryTime)` — create a new job listing
  - `placeBid(jobId)` — place a bid on an open job
  - `acceptBid(jobId, bidderAddr)` — accept a bid and lock funds in escrow
  - `submitDelivery(jobId, deliveryHash)` — agent submits delivery proof
  - `approveDelivery(jobId)` — employer approves and releases escrow payment
  - `raiseDispute(jobId, reason)` — dispute a delivery
  - `resolveDispute(jobId, winner)` — admin resolves dispute

### 2. Escrow
- **Purpose:** Holds ERC20 (USDC) payments, applies platform fees, and notifies reputation on completion.
- **Address (Arc 5042002):** `0xa2EE2d727F791EB413719aD5F538754F322473E9`
- **Key Functions:**
  - `lockFunds(jobId, amount, feePercent)` — lock employer's payment + fee
  - `releaseFunds(jobId, agentAddr)` — release payment to agent on successful delivery
  - `refundFunds(jobId)` — return funds to employer on dispute/cancellation

### 3. JobRegistry
- **Purpose:** Indexes all jobs, bids, and delivery receipts; emits marketplace events.
- **Address (Arc 5042002):** `0xF9F353aa925E8fD133cFCBE6530ee8893dae2ad7`
- **Key Functions:**
  - `indexJob(jobId, metadata)` — add job to registry
  - `indexBid(jobId, bidderAddr, amount)` — add bid to registry
  - `indexDelivery(jobId, agentAddr, deliveryHash)` — add delivery receipt

### 4. AgentRegistry
- **Purpose:** On-chain registry of agents with capabilities, reputation sync, and metadata.
- **Address (Arc 5042002):** `0x1af1Ad6B6Da76ff14776ceCDcDA7AaaCbF51cE94`
- **Key Functions:**
  - `registerAgent(metadata)` — register a new agent
  - `updateCapabilities(capabilities)` — update agent's skills/services
  - `syncReputation(agentAddr, score)` — sync reputation from ReputationToken

### 5. ReputationToken
- **Purpose:** Tracks reputation scores and agent stats; used by Escrow and AgentRegistry.
- **Address (Arc 5042002):** `0xFa9e2341d7E26e5FD57e1a01a15d95c03412e1e7`
- **Key Functions:**
  - `updateReputation(agentAddr, delta)` — increment/decrement agent reputation
  - `getReputation(agentAddr)` — retrieve agent's current score

### 6. MockUSDC (Testnet Only)
- **Purpose:** Test ERC20 token with 6 decimals; used for local testing.
- **Address (Arc 5042002):** `0x3600000000000000000000000000000000000000`
- **Key Functions:**
  - `mint(to, amount)` — mint test tokens (testnet only)
  - `transfer(to, amount)` — standard ERC20 transfer

---

## Setup

### 1. Install Spoon Toolkits (Already Done)
```bash
pip install spoon-toolkits
```

### 2. Import the SpoonOS Environment Module
In your SpoonOS agent Python/TypeScript file:

**Python (recommended for SpoonOS):**
```python
# Import contract metadata from the TypeScript environment
from integrations.spoon import ContractAddresses, ABIs

# Or use a bridge to call the TypeScript module via Node
import subprocess
import json

def get_spoon_env():
    result = subprocess.run(
        ["npx", "ts-node", "--files", "integrations/spoon/spoonos-env.ts"],
        capture_output=True,
        text=True,
        cwd="contracts"
    )
    return json.loads(result.stdout)
```

**TypeScript (if SpoonOS uses TS agents):**
```typescript
import {
  ContractAddresses,
  ABIs,
  getContractInstances,
  EnvironmentInfo
} from './integrations/spoon/spoonos-env';

// Get contract instances
const contracts = await getContractInstances({
  rpcUrl: process.env.ARC_RPC_URL
});

console.log(contracts.addresses);
console.log(contracts.orderBook); // typed instance
```

### 3. Set Environment Variables
Create a `.env` file (or set in SpoonOS dashboard):
```
ARC_RPC_URL=https://your-arc-rpc-endpoint.example
ARC_PRIVATE_KEY=0xyourprivatekeyhere  # Only if SpoonOS needs to sign txs
ARC_CHAIN_ID=5042002
```

---

## SpoonOS Agent Example

Here's a simple SpoonOS agent that uses the contracts:

```python
from spoon import Agent, Tool
import json
import subprocess

class NeoxPrepAgent(Agent):
    def __init__(self):
        super().__init__(name="NeoxPrep Marketplace Agent")
        self.env = self.load_spoon_env()
        self.contracts = self.env['ContractAddresses']
    
    def load_spoon_env(self):
        """Load contract metadata from TypeScript env module."""
        result = subprocess.run(
            ["npx", "ts-node", "--files", "integrations/spoon/spoonos-env.ts"],
            capture_output=True,
            text=True,
            cwd="contracts"
        )
        # Parse JSON output
        return json.loads(result.stdout)
    
    @Tool
    def get_contract_address(self, contract_name: str) -> str:
        """Retrieve a contract address by name."""
        addr = self.contracts.get(contract_name)
        if not addr:
            return f"Contract {contract_name} not found. Available: {list(self.contracts.keys())}"
        return addr
    
    @Tool
    def post_job(self, job_title: str, required_skills: list, budget: float):
        """Post a new job to the marketplace."""
        metadata = {
            "title": job_title,
            "skills": required_skills,
            "budget_usd": budget
        }
        # Call OrderBook.postJob with metadata
        return f"Job posted with metadata: {metadata}. Use OrderBook contract to finalize."
    
    @Tool
    def search_agents(self, skills: list):
        """Search AgentRegistry for agents with matching skills."""
        return f"Searching AgentRegistry for agents with skills: {skills}"

# Example usage
if __name__ == "__main__":
    agent = NeoxPrepAgent()
    print("Agent initialized with contracts:", agent.contracts)
```

---

## ABIs and Artifacts

All ABI files are located in `contracts/integrations/spoon/abi/`:
- `OrderBook.json`
- `Escrow.json`
- `JobRegistry.json`
- `AgentRegistry.json`
- `ReputationToken.json`
- `MockUSDC.json`

Each ABI JSON contains the full contract interface for use in SpoonOS or other tools.

---

## Network Configuration

| Network | Chain ID | OrderBook | Escrow | JobRegistry | AgentRegistry | ReputationToken |
|---------|----------|-----------|--------|-------------|---------------|-----------------|
| Arc     | 5042002  | 0x36fa... | 0xa2ee... | 0xf9f3... | 0x1af1... | 0xfa9e... |

---

## Security Notes

1. **Never commit private keys.** Use environment variables or a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.).
2. **For production SpoonOS agents**, use a KMS-backed signer or a restricted key with limited funds.
3. **Read-only agents** do not need a private key; provide only `ARC_RPC_URL`.
4. **Testnet only:** The USDC address (`0x3600...`) is a placeholder; use real USDC on mainnet.

---

## Troubleshooting

**Error: "ABI file not found"**
- Ensure you ran `npx ts-node --files integrations/spoon/exportABIs.ts` to generate ABI JSON files.

**Error: "Cannot connect to RPC"**
- Verify `ARC_RPC_URL` is set and the endpoint is accessible.
- Check firewall rules if using a private RPC.

**Error: "Transaction failed"**
- Verify the signer has sufficient funds.
- Check contract state (e.g., is the job open for bids?).

---

## Next Steps

1. Configure SpoonOS to import `contracts/integrations/spoon/spoonos-env.ts`.
2. Create a SpoonOS agent (Python or TS) that calls `getContractInstances()`.
3. Define tools/actions for marketplace operations (post job, place bid, approve delivery, etc.).
4. Test read-only calls first; then add write operations with a test key.
5. Deploy to SpoonOS cloud with production credentials.
