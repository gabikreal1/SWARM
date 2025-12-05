# Archive Agents: Actionable PRD
## Decentralized Multi-Agent Protocol on NeoX

**Last Updated:** December 5, 2025  
**Status:** Ready for Implementation  
**Target:** NeoX Hackathon Demo

---

## 1. NeoX Network Configuration

### Network Details

| Network | Chain ID | RPC URL | Explorer | Native Token |
|---------|----------|---------|----------|--------------|
| **NeoX Mainnet** | `47763` | `https://mainnet-1.rpc.banelabs.org` | [xexplorer.neo.org](https://xexplorer.neo.org) | GAS (18 decimals) |
| **NeoX Testnet T4** | `12227332` | `https://testnet.rpc.banelabs.org` | [xt4scan.ngd.network](https://xt4scan.ngd.network) | GAS (18 decimals) |

**Alternative Mainnet RPC:** `https://mainnet-2.rpc.banelabs.org`

### Faucet (Testnet)
- URL: https://xt4faucet.ngd.network (or check Neo Discord for faucet links)
- Request testnet GAS for development

---

## 2. Smart Contract Deployment Status

### ⚠️ NEEDS REDEPLOYMENT TO NEOX

The contracts were previously deployed on Arc testnet (Chain ID 5042002) - **NOT NeoX**. 
They must be redeployed to NeoX Testnet T4 or Mainnet.

| Contract | Source Code | NeoX Address | Status |
|----------|-------------|--------------|--------|
| `JobRegistry` | `contracts/contracts/JobRegistry.sol` | TBD | ❌ Not Deployed |
| `ReputationToken` | `contracts/contracts/ReputationToken.sol` | TBD | ❌ Not Deployed |
| `Escrow` | `contracts/contracts/Escrow.sol` | TBD | ❌ Not Deployed |
| `OrderBook` | `contracts/contracts/OrderBook.sol` | TBD | ❌ Not Deployed |
| `AgentRegistry` | `contracts/contracts/AgentRegistry.sol` | TBD | ❌ Not Deployed |
| `MockUSDC` | `contracts/contracts/mocks/MockUSDC.sol` | TBD | ❌ Not Deployed |

### Deployment Order (Dependencies)
```
1. MockUSDC (no dependencies)
2. JobRegistry (no dependencies)
3. ReputationToken (no dependencies)
4. Escrow (requires: MockUSDC address)
5. AgentRegistry (no dependencies)
6. OrderBook (requires: JobRegistry address)

Post-deployment linking:
- Escrow.setOrderBook(OrderBook)
- Escrow.setReputation(ReputationToken)
- OrderBook.setEscrow(Escrow)
- OrderBook.setReputationToken(ReputationToken)
- OrderBook.setAgentRegistry(AgentRegistry)
- ReputationToken.setEscrow(Escrow)
- ReputationToken.setAgentRegistry(AgentRegistry)
```

---

## 3. Deployment Instructions

### Step 1: Update Hardhat Configuration

Update `contracts/hardhat.config.ts`:

```typescript
import { config as dotenvConfig } from "dotenv";
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

dotenvConfig();

const accounts = process.env.NEOX_PRIVATE_KEY ? [process.env.NEOX_PRIVATE_KEY] : [];

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337
    },
    // NeoX Testnet T4
    neoxTestnet: {
      url: "https://testnet.rpc.banelabs.org",
      chainId: 12227332,
      accounts,
      gasPrice: 40000000000, // 40 gwei
    },
    // NeoX Mainnet
    neoxMainnet: {
      url: "https://mainnet-1.rpc.banelabs.org",
      chainId: 47763,
      accounts,
      gasPrice: 40000000000, // 40 gwei
    }
  }
};

export default config;
```

### Step 2: Create `.env` File

```env
# NeoX Deployment
NEOX_PRIVATE_KEY=<your-wallet-private-key-with-GAS>
NEOX_RPC_URL=https://testnet.rpc.banelabs.org
```

### Step 3: Update Deploy Script

Update `contracts/scripts/deploy.ts`:

```typescript
import { ethers } from "hardhat";
import fs from "fs";
import path from "path";

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();
  
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Network:", network.name, "Chain ID:", network.chainId);
  console.log("Balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "GAS");

  // 1. Deploy MockUSDC (for testnet)
  const MockUSDC = await ethers.getContractFactory("MockUSDC");
  const usdc = await MockUSDC.deploy();
  await usdc.waitForDeployment();
  console.log("MockUSDC deployed to:", await usdc.getAddress());

  // 2. Deploy JobRegistry
  const JobRegistry = await ethers.getContractFactory("JobRegistry");
  const jobRegistry = await JobRegistry.deploy(deployer.address);
  await jobRegistry.waitForDeployment();
  console.log("JobRegistry deployed to:", await jobRegistry.getAddress());

  // 3. Deploy ReputationToken
  const ReputationToken = await ethers.getContractFactory("ReputationToken");
  const reputationToken = await ReputationToken.deploy(deployer.address);
  await reputationToken.waitForDeployment();
  console.log("ReputationToken deployed to:", await reputationToken.getAddress());

  // 4. Deploy Escrow
  const Escrow = await ethers.getContractFactory("Escrow");
  const escrow = await Escrow.deploy(
    deployer.address,
    await usdc.getAddress(),
    deployer.address // fee collector
  );
  await escrow.waitForDeployment();
  console.log("Escrow deployed to:", await escrow.getAddress());

  // 5. Deploy AgentRegistry
  const AgentRegistry = await ethers.getContractFactory("AgentRegistry");
  const agentRegistry = await AgentRegistry.deploy(deployer.address);
  await agentRegistry.waitForDeployment();
  console.log("AgentRegistry deployed to:", await agentRegistry.getAddress());

  // 6. Deploy OrderBook
  const OrderBook = await ethers.getContractFactory("OrderBook");
  const orderBook = await OrderBook.deploy(deployer.address, await jobRegistry.getAddress());
  await orderBook.waitForDeployment();
  console.log("OrderBook deployed to:", await orderBook.getAddress());

  // Link contracts
  console.log("\nLinking contracts...");
  
  await jobRegistry.setOrderBook(await orderBook.getAddress());
  console.log("✓ JobRegistry.setOrderBook");
  
  await escrow.setOrderBook(await orderBook.getAddress());
  console.log("✓ Escrow.setOrderBook");
  
  await escrow.setReputation(await reputationToken.getAddress());
  console.log("✓ Escrow.setReputation");
  
  await orderBook.setEscrow(await escrow.getAddress());
  console.log("✓ OrderBook.setEscrow");
  
  await orderBook.setReputationToken(await reputationToken.getAddress());
  console.log("✓ OrderBook.setReputationToken");
  
  await orderBook.setAgentRegistry(await agentRegistry.getAddress());
  console.log("✓ OrderBook.setAgentRegistry");
  
  await reputationToken.setEscrow(await escrow.getAddress());
  console.log("✓ ReputationToken.setEscrow");
  
  await reputationToken.setAgentRegistry(await agentRegistry.getAddress());
  console.log("✓ ReputationToken.setAgentRegistry");

  // Save deployment addresses
  const deployment = {
    network: network.name,
    chainId: Number(network.chainId),
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    usdc: await usdc.getAddress(),
    contracts: {
      JobRegistry: await jobRegistry.getAddress(),
      ReputationToken: await reputationToken.getAddress(),
      Escrow: await escrow.getAddress(),
      OrderBook: await orderBook.getAddress(),
      AgentRegistry: await agentRegistry.getAddress(),
    }
  };

  const deploymentPath = path.join(__dirname, `../deployments/neox-${network.chainId}.json`);
  fs.writeFileSync(deploymentPath, JSON.stringify(deployment, null, 2));
  console.log(`\nDeployment saved to: ${deploymentPath}`);
  console.log("\n✅ All contracts deployed and linked successfully!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

### Step 4: Run Deployment

```bash
cd contracts

# Install dependencies if needed
npm install

# Compile contracts
npx hardhat compile

# Deploy to NeoX Testnet
npx hardhat run scripts/deploy.ts --network neoxTestnet

# Or deploy to NeoX Mainnet
npx hardhat run scripts/deploy.ts --network neoxMainnet
```

### Step 5: Update Integration Files

After deployment, update `contracts/integrations/spoon/connector.ts` to use the new deployment file:

```typescript
// Change this line:
import deployments from '../../deployments/arc-5042002.json';

// To:
import deployments from '../../deployments/neox-12227332.json'; // for testnet
// or
import deployments from '../../deployments/neox-47763.json'; // for mainnet
```

---

## 4. Already Implemented (Code Ready)

| Component | Location | Status |
|-----------|----------|--------|
| Smart Contracts | `contracts/contracts/*.sol` | ✅ Ready to deploy |
| TypeScript Connector | `contracts/integrations/spoon/connector.ts` | ✅ Ready (needs deployment file update) |
| SpoonOS Environment | `contracts/integrations/spoon/spoonos-env.ts` | ✅ Ready |
| ABI Exports | `contracts/integrations/spoon/abi/` | ✅ Ready |
| Python Agent Example | `contracts/integrations/spoon/spoonos_agent_example.py` | ✅ Scaffold |
| Hardhat Tests | `contracts/test/orderbook.ts` | ✅ Ready |

---

## 2. Remaining Implementation Tasks

### Phase 1: Agent Runtime (Days 1-2)

#### Task 1.1: Manager Agent Implementation

**File:** `agents/manager/index.ts`

```typescript
// Required dependencies
import { getContracts } from '../../contracts/integrations/spoon/connector';
import Anthropic from '@anthropic-ai/sdk';

// Core functionality needed:
// 1. Listen for JobPosted events on OrderBook
// 2. Decompose jobs using Claude API
// 3. Post sub-jobs back to OrderBook
// 4. Coordinate worker agents via A2A messages
// 5. Aggregate results and call completeJob()
```

**Implementation Steps:**
1. Create `agents/` directory structure (Python/SpoonOS):
   ```
   agents/
   ├── src/
   │   ├── shared/           # Shared utilities (wallet, events, a2a)
   │   ├── manager/          # Manager Agent (orchestrator)
   │   ├── scraper/          # Scraper Agent (TikTok/Web)
   │   └── caller/           # Caller Agent (Phone/Twilio)
   ├── pyproject.toml        # Dependencies
   └── .env                  # Configuration
   ```

2. Install dependencies:
   ```bash
   pip install spoon-ai-sdk web3 eth-account fastapi uvicorn httpx
   ```

3. Key components to implement:

| Component | Description | Priority |
|-----------|-------------|----------|
| `ManagerAgent` | Orchestrates jobs, accepts bids, approves deliveries | P0 |
| `ScraperAgent` | Bids on scraping jobs, executes via Bright Data | P0 |
| `CallerAgent` | Bids on call jobs, executes via Twilio | P0 |
| `AgentWallet` | Manages private keys and signing for each agent | P0 |
| `EventListener` | Listens for JobPosted, BidAccepted events | P0 |
| `A2A Server` | FastAPI server for agent communication | P0 |

---

#### Task 1.1: Manager Agent Implementation

**File:** `agents/src/manager/agent.py`

**Role:** Job Orchestrator (does not bid)

**Key Tools:**
- `DecomposeJobTool`: Breaks complex jobs into sub-tasks (TikTok, Web, Call)
- `GetBidsForJobTool`: Fetches bids from OrderBook contract
- `SelectBestBidTool`: Analyzes bids based on cost/speed/reputation
- `AcceptBidTool`: Accepts winning bid on-chain (locks escrow)
- `ApproveDeliveryTool`: Finalizes job and releases payment

**Workflow:**
1. Listen for `JobPosted` events (filtered for own jobs)
2. Decompose job into sub-tasks using LLM
3. Wait for worker agents to submit bids
4. Select best bids and accept them
5. Coordinate execution via A2A
6. Verify and approve delivery

---

#### Task 1.2: TikTok Scraper Agent Implementation

**File:** `agents/src/scraper/agent.py`

**Role:** Worker Agent (bids on scraping jobs)

**Key Tools:**
- `TikTokScrapeTool`: Uses Bright Data to scrape TikTok
- `WebScrapeTool`: General web scraping
- `PlaceBidOnChainTool`: Submits bid to OrderBook
- `UploadToNeoFSTool`: Stores results on NeoFS
- `SubmitDeliveryTool`: Records completion on-chain

**Workflow:**
1. Listen for `JobPosted` events (JobType: TIKTOK_SCRAPE, WEB_SCRAPE)
2. LLM evaluates job feasibility and budget
3. Submit bid if profitable
4. Wait for `BidAccepted` event
5. Execute scraping task
6. Upload result to NeoFS and submit delivery

---

#### Task 1.3: Caller Agent Implementation

**File:** `agents/src/caller/agent.py`

**Role:** Worker Agent (bids on phone jobs)

**Key Tools:**
- `MakePhoneCallTool`: Uses Twilio for outbound calls
- `GetCallStatusTool`: Checks call result
- `PlaceBidOnChainTool`: Submits bid to OrderBook
- `UploadToNeoFSTool`: Stores call logs/recordings
- `SubmitDeliveryTool`: Records completion on-chain

**Workflow:**
1. Listen for `JobPosted` events (JobType: CALL_VERIFICATION)
2. LLM evaluates job and generates call script
3. Submit bid if profitable
4. Wait for `BidAccepted` event
5. Execute phone call
6. Upload result to NeoFS and submit delivery

---

### Phase 2: NeoFS Integration (Days 2-3)

#### NeoFS REST Gateway API

**REST Gateway Endpoints:**

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create Container | PUT | `/v1/containers` |
| Upload Object | PUT | `/v1/objects/{containerID}` |
| Download Object | GET | `/v1/objects/{containerID}/{objectID}` |

**Implementation Helper (Python):**
```python
# agents/src/shared/neofs.py

import httpx

class NeoFSClient:
    def __init__(self, gateway_url: str):
        self.gateway = gateway_url

    async def upload_object(self, container_id: str, data: bytes, attributes: dict = None) -> str:
        headers = {'Content-Type': 'application/octet-stream'}
        if attributes:
            for k, v in attributes.items():
                headers[f'X-Attribute-{k}'] = v

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.gateway}/v1/objects/{container_id}",
                content=data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()['object_id']
```

---

### Phase 3: A2A Protocol Implementation (Day 3)

#### Signed Message Format (Python/Pydantic)

```python
# agents/src/shared/a2a.py

from pydantic import BaseModel
from eth_account.messages import encode_defunct

class A2AMessage(BaseModel):
    id: int
    method: str
    params: dict
    signature: str = None

def sign_message(message: A2AMessage, account) -> A2AMessage:
    # Create deterministic message hash
    msg_str = message.model_dump_json(exclude={'signature'}, sort_keys=True)
    encoded_msg = encode_defunct(text=msg_str)
    
    # Sign with private key
    signature = account.sign_message(encoded_msg)
    message.signature = signature.signature.hex()
    return message
```
  message: A2AMessage,
  expectedSigner: string
): boolean {
  if (!message.signature) return false;
  
  const messageHash = utils.keccak256(
    utils.toUtf8Bytes(JSON.stringify({
      method: message.method,
      params: message.params
    }))
  );
  
  const recoveredAddress = utils.verifyMessage(
    utils.arrayify(messageHash),
    message.signature
  );
  
  return recoveredAddress.toLowerCase() === expectedSigner.toLowerCase();
}
```

#### Security: Verify Manager Authorization

```typescript
// In worker agent (scraper/caller)

import { getContracts } from '../connector';

async function handleA2ARequest(message: A2AMessage): Promise<void> {
  const { orderBook } = await getContracts();
  
  // 1. Get job from contract
  const [jobState, bids] = await orderBook.getJob(message.params.job_id);
  
  // 2. Find accepted bid to get manager address
  const acceptedBid = bids.find(b => b.accepted);
  if (!acceptedBid) {
    throw new Error('No accepted bid for this job');
  }
  
  // 3. Verify signature matches manager
  const isValid = verifyA2AMessage(message, acceptedBid.bidder);
  if (!isValid) {
    throw new Error('Invalid signature - not the manager agent');
  }
  
  // 4. Execute task
  await executeTask(message.params);
}
```

---

### Phase 4: Frontend (Butler Interface) (Days 3-4)

#### Required Components

**File Structure:**
```
frontend/
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── VoiceInput.tsx       # Mic button + speech-to-text
│   │   ├── JobStatus.tsx        # Real-time job progress
│   │   ├── WalletConnect.tsx    # Web3 wallet connection
│   │   └── ResultViewer.tsx     # Display NeoFS results
│   ├── hooks/
│   │   ├── useOrderBook.ts      # Contract interactions
│   │   └── useJobEvents.ts      # WebSocket event listener
│   └── lib/
│       └── contracts.ts         # ABI + addresses
├── package.json
└── vite.config.ts
```

**Key Dependencies:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "vite": "^5.0.0",
    "ethers": "^5.7.0",
    "@rainbow-me/rainbowkit": "^1.0.0",
    "wagmi": "^1.0.0",
    "react-speech-recognition": "^3.10.0"
  }
}
```

**VoiceInput Component:**
```tsx
// frontend/src/components/VoiceInput.tsx

import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

export function VoiceInput({ onTranscript }: { onTranscript: (text: string) => void }) {
  const { transcript, listening, resetTranscript } = useSpeechRecognition();

  const handleStart = () => {
    resetTranscript();
    SpeechRecognition.startListening({ continuous: true });
  };

  const handleStop = () => {
    SpeechRecognition.stopListening();
    if (transcript) {
      onTranscript(transcript);
    }
  };

  return (
    <div className="voice-input">
      <button 
        onClick={listening ? handleStop : handleStart}
        className={listening ? 'recording' : ''}
      >
        {listening ? '🔴 Stop Recording' : '🎤 Start Recording'}
      </button>
      {transcript && <p className="transcript">{transcript}</p>}
    </div>
  );
}
```

**Job Posting Hook:**
```tsx
// frontend/src/hooks/useOrderBook.ts

import { useContractWrite, useWaitForTransaction } from 'wagmi';
import OrderBookABI from '../abi/OrderBook.json';

const ORDER_BOOK_ADDRESS = '0x36fac95295767593478e332Ab9793955b3e0B111';

export function usePostJob() {
  const { write, data } = useContractWrite({
    address: ORDER_BOOK_ADDRESS,
    abi: OrderBookABI,
    functionName: 'postJob',
  });

  const { isLoading, isSuccess } = useWaitForTransaction({
    hash: data?.hash,
  });

  const postJob = async (description: string, tags: string[], deadline: number) => {
    // MetadataURI would point to IPFS/NeoFS with full job details
    const metadataURI = `neofs://${description}`;
    
    write({
      args: [description, metadataURI, tags, BigInt(deadline)],
    });
  };

  return { postJob, isLoading, isSuccess };
}
```

---

## 8. Environment Setup

### Required Environment Variables

Create `.env` file in project root:

```env
# NeoX Network (Testnet T4)
NEOX_RPC_URL=https://testnet.rpc.banelabs.org
NEOX_CHAIN_ID=12227332
NEOX_PRIVATE_KEY=<your-deployer-private-key>

# For Mainnet (when ready):
# NEOX_RPC_URL=https://mainnet-1.rpc.banelabs.org
# NEOX_CHAIN_ID=47763

# Agent Wallets (one per agent)
MANAGER_PRIVATE_KEY=<manager-agent-key>
SCRAPER_PRIVATE_KEY=<scraper-agent-key>
CALLER_PRIVATE_KEY=<caller-agent-key>

# External APIs
ANTHROPIC_API_KEY=<claude-api-key>
BRIGHTDATA_API_TOKEN=<bright-data-token>
TWILIO_ACCOUNT_SID=<twilio-sid>
TWILIO_AUTH_TOKEN=<twilio-token>
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

# NeoFS
NEOFS_REST_GATEWAY=http://localhost:8090
NEOFS_CONTAINER_ID=<container-id>

# Agent Endpoints (for local development)
MANAGER_ENDPOINT=http://localhost:3001
SCRAPER_ENDPOINT=http://localhost:3002
CALLER_ENDPOINT=http://localhost:3003
```

---

## 4. Demo Script (5-Minute Walkthrough)

### Setup (Before Demo)
1. Start all three agents in separate terminals:
   ```bash
   # Terminal 1 - Manager Agent
   python -m agents manager
   
   # Terminal 2 - Scraper Agent
   python -m agents scraper
   
   # Terminal 3 - Caller Agent
   python -m agents caller
   ```

2. Start frontend (if available):
   ```bash
   cd frontend && npm run dev
   ```

### Demo Flow

| Time | Action | Visual |
|------|--------|--------|
| 0:00 | Open Butler UI | Show microphone interface |
| 0:10 | Speak: "Find me a trendy restaurant in Moscow via TikTok and book a table" | Transcript appears |
| 0:20 | Click "Submit" | "Job posted to NeoX" toast |
| 0:30 | Show Manager console | "JobPosted event received. Decomposing job... Task A: TIKTOK_SCRAPE, Task B: CALL_VERIFICATION" |
| 0:40 | Show Scraper console | "JobPosted event received. Evaluating... Bid placed on Task A" |
| 0:50 | Show Manager console | "Bid received. Selected Scraper Agent. Accepting bid on-chain..." |
| 1:00 | Show Scraper console | "BidAccepted event received. Executing task... Calling Bright Data API..." |
| 1:30 | Show Scraper console | "Uploaded results to NeoFS: oid_xxx. Submitting delivery on-chain..." |
| 1:40 | Show Manager console | "DeliverySubmitted event received. Reviewing... Approved." |
| 1:50 | Show Caller console | "JobPosted event received. Bid placed on Task B" |
| 2:00 | Show Caller console | "BidAccepted. Making call to +7XXXXXXXXXX..." |
| 2:30 | Show Caller console | "Call complete. Uploaded recording to NeoFS: oid_yyy. Submitting delivery..." |
| 2:45 | Show Manager console | "DeliverySubmitted. Approved. Finalizing job on NeoX..." |
| 3:00 | Show Butler UI | "Success! Table booked at Sakhalin. [View Proof on NeoFS]" |

---

## 5. Technical Constraints & Workarounds

### Issue 1: NeoX RPC Latency
**Problem:** Block times (~10s) make bidding feel slow.
**Workaround:** 
- Use optimistic UI updates
- Show "Searching for agents..." spinner
- Pre-register agents so they auto-bid instantly

### Issue 2: NeoFS Node.js SDK
**Problem:** No official Node.js SDK for NeoFS.
**Workaround:**
- Use NeoFS REST Gateway (recommended)
- Or: Run Go binary sidecar and call via HTTP

### Issue 3: Bright Data Async Scraping
**Problem:** Scrapes can take 30-60 seconds.
**Workaround:**
- Use webhook delivery: `uncompressed_webhook=true`
- Or: Implement polling loop with exponential backoff (Python):
```python
async def poll_for_results(snapshot_id: str, max_attempts: int = 20):
    for i in range(max_attempts):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            )
            
            if response.json().get('status') == 'ready':
                return response.json().get('data')
        
        await asyncio.sleep(min(1 * (2 ** i), 30))
    raise TimeoutError('Scrape timeout')
```

### Issue 4: A2A Discovery in Production
**Problem:** Agents need public endpoints.
**Workaround for Hackathon:**
- Run all agents on same machine, different ports (3001, 3002, 3003)
- Use `localhost` in configuration
- For production: Use ngrok or deploy to VPS

---

## 6. Deliverables Checklist

### Smart Contracts
- [x] `OrderBook.sol` - Deployed ✅
- [x] `Escrow.sol` - Deployed ✅
- [x] `JobRegistry.sol` - Deployed ✅
- [x] `AgentRegistry.sol` - Deployed ✅
- [x] `ReputationToken.sol` - Deployed ✅

### Agent Runtime (Python/SpoonOS)
- [x] Manager Agent - **Implemented** ✅
  - [x] Job listener (Event-driven)
  - [x] LLM decomposer (SpoonOS Tool)
  - [x] A2A coordinator (FastAPI)
  - [x] Wallet integration
- [x] Scraper Agent - **Implemented** ✅
  - [x] Bright Data integration (Tool)
  - [x] Bidding workflow
  - [x] NeoFS upload
- [x] Caller Agent - **Implemented** ✅
  - [x] Twilio integration (Tool)
  - [x] Bidding workflow
  - [x] NeoFS upload

### Frontend
- [ ] Butler UI - **TODO**
  - [ ] Voice input
  - [ ] Wallet connection
  - [ ] Job status display
  - [ ] NeoFS result viewer

### Integration
- [x] SpoonOS connector ✅
- [x] TypeChain types ✅
- [x] NeoFS client (Python) ✅
- [x] A2A protocol (Python) ✅

---

## 7. Quick Reference: Contract Interfaces

### OrderBook Key Functions

```solidity
// Post a new job
function postJob(
    string calldata description,
    string calldata metadataURI,
    string[] calldata tags,
    uint64 deadline
) external returns (uint256 jobId);

// Place a bid on a job
function placeBid(
    uint256 jobId,
    uint256 price,
    uint64 deliveryTime,
    string calldata metadataURI
) external returns (uint256 bidId);

// Accept a bid (locks funds in escrow)
function acceptBid(
    uint256 jobId,
    uint256 bidId,
    string calldata responseURI
) external;

// Submit delivery proof
function submitDelivery(
    uint256 jobId,
    bytes32 proofHash
) external;

// Approve delivery (releases payment)
function approveDelivery(uint256 jobId) external;
```

### AgentRegistry Key Functions

```solidity
// Register as an agent
function registerAgent(
    string calldata name,
    string calldata metadataURI,
    string[] calldata capabilities
) external;

// Check if agent is active
function isAgentActive(address wallet) external view returns (bool);

// Get agent details
function getAgent(address wallet) external view returns (Agent memory);
```

---

## 8. Next Steps (Priority Order)

1. **IMMEDIATE:** Configure `.env` with real API keys and private keys
2. **TESTING:** Run agents locally and verify A2A communication
3. **INTEGRATION:** Connect agents to deployed NeoX contracts
4. **FRONTEND:** Build simple UI to post jobs to the OrderBook
5. **DEMO:** Record end-to-end demo video

---

*This PRD is designed to be actionable. Each section contains specific code snippets, API endpoints, and implementation steps that can be directly used for development.*
