# Archive Agents - SpoonOS-based Multi-Agent System

Decentralized multi-agent protocol built on SpoonOS framework for NeoX blockchain.

## Architecture

```
agents/
├── src/
│   ├── shared/               # Shared utilities
│   │   ├── config.py         # Configuration management
│   │   ├── contracts.py      # Web3 contract interactions
│   │   ├── a2a.py            # Agent-to-Agent protocol
│   │   ├── neofs.py          # NeoFS storage client
│   │   ├── wallet.py         # Wallet management (each agent has own wallet)
│   │   ├── events.py         # Blockchain event listening
│   │   ├── base_agent.py     # Base class for worker agents
│   │   ├── wallet_tools.py   # Tools for wallet operations
│   │   └── bidding_tools.py  # Tools for bidding workflow
│   │
│   ├── manager/              # Manager Agent (orchestrator)
│   │   ├── agent.py          # Job orchestration agent
│   │   ├── tools.py          # Decomposition, bid acceptance, coordination
│   │   └── server.py         # A2A endpoint server
│   │
│   ├── scraper/              # Scraper Agent (TikTok/Web)
│   │   ├── agent.py          # Scraper agent with bidding
│   │   ├── tools.py          # Bright Data scraping tools
│   │   └── server.py         # A2A endpoint server
│   │
│   └── caller/               # Caller Agent (Phone/Twilio)
│       ├── agent.py          # Caller agent with bidding
│       ├── tools.py          # Twilio calling tools
│       └── server.py         # A2A endpoint server
│
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Key Features

### 1. Each Agent Has Its Own Wallet
Every agent (Manager, Scraper, Caller) has its own wallet for:
- Receiving payments from completed jobs
- Paying for on-chain transactions
- Signing A2A messages for authentication

### 2. Event-Driven Architecture
Agents listen for blockchain events:
- **JobPosted**: Worker agents evaluate and bid
- **BidAccepted**: Workers start execution
- **DeliverySubmitted**: Manager reviews and approves

### 3. LLM-Driven Bidding Decisions
When a job is posted, the agent's LLM evaluates:
- Can I complete this task?
- What should I bid?
- Is the budget sufficient?

## Setup

1. Create virtual environment:
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and private keys
```

## Running Agents

Use the CLI to run agents:

```bash
# Terminal 1 - Manager Agent (port 3001)
python -m agents manager

# Terminal 2 - Scraper Agent (port 3002)
python -m agents scraper

# Terminal 3 - Caller Agent (port 3003)
python -m agents caller

# Override port
python -m agents manager --port 8001
```

Or run servers directly:

```bash
python -m agents.src.manager.server
python -m agents.src.scraper.server
python -m agents.src.caller.server
```

## Agent Workflow

### Worker Agents (Scraper, Caller)

```
1. JobPosted event detected
   ↓
2. LLM evaluates job (using bidding prompt)
   "Can I do this? What should I bid?"
   ↓
3. If yes, prepare and place bid on-chain
   ↓
4. BidAccepted event for our bid
   ↓
5. Execute job using agent-specific tools
   ↓
6. Upload results to NeoFS
   ↓
7. Submit delivery on-chain with proof hash
```

### Manager Agent (Orchestrator)

```
1. Receive job request or watch for our JobPosted events
   ↓
2. Decompose complex job into sub-tasks
   ↓
3. Wait for worker bids to come in
   ↓
4. Analyze bids and select best workers
   ↓
5. Accept winning bids (lock escrow)
   ↓
6. Monitor delivery submissions
   ↓
7. Approve deliveries and release payments
```

## SpoonOS Agent Pattern

Each agent follows the SpoonOS `ToolCallAgent` pattern:

```python
from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot

class MyAgent(ToolCallAgent):
    name: str = "my_agent"
    description: str = "Agent description"
    system_prompt: str = "You are a helpful assistant..."
    max_steps: int = 10
    
    available_tools: ToolManager = Field(
        default_factory=lambda: ToolManager([MyCustomTool()])
    )
```

## Agent Responsibilities

### Manager Agent
- Listens for `JobPosted` events on OrderBook contract
- Decomposes complex jobs into sub-tasks using LLM
- Coordinates worker agents via A2A protocol
- Aggregates results and finalizes jobs on-chain

### Scraper Agent
- Bids on scraping jobs (TikTok, web)
- Uses Bright Data API for TikTok scraping
- Uploads results to NeoFS
- Reports completion via A2A

### Caller Agent
- Bids on phone verification jobs
- Uses Twilio for outbound calls
- Records call outcomes
- Uploads proof to NeoFS

## Environment Variables

```bash
# Blockchain
NEOX_RPC_URL=https://testnet.rpc.banelabs.org
NEOX_CHAIN_ID=12227332

# Agent Private Keys
MANAGER_PRIVATE_KEY=0x...
SCRAPER_PRIVATE_KEY=0x...
CALLER_PRIVATE_KEY=0x...

# Contract Addresses
ORDERBOOK_ADDRESS=0x...
AGENT_REGISTRY_ADDRESS=0x...
ESCROW_ADDRESS=0x...
REPUTATION_TOKEN_ADDRESS=0x...

# External APIs
BRIGHT_DATA_API_KEY=...        # For TikTok scraping
TWILIO_ACCOUNT_SID=...         # For phone calls
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# NeoFS
NEOFS_ENDPOINT=https://rest.fs.neo.org
NEOFS_CONTAINER_ID=...

# LLM
ANTHROPIC_API_KEY=...
# or OPENAI_API_KEY=...
```

## A2A Protocol

Agents communicate using a JSON-RPC style A2A protocol:

```json
{
  "jsonrpc": "2.0",
  "id": "123",
  "method": "execute_task",
  "params": {
    "job_id": 1,
    "task_type": "tiktok_scrape",
    "description": "...",
    "parameters": {}
  },
  "sender": "0xManagerAddress",
  "timestamp": 1234567890,
  "signature": "0x..."
}
```

Supported methods:
- `ping` - Health check
- `get_capabilities` - Query agent capabilities
- `get_status` - Query agent status
- `execute_task` - Request task execution

## Blockchain Integration

The agents interact with these smart contracts:

- **OrderBook** - Job posting and bidding
- **AgentRegistry** - Agent registration and capabilities
- **Escrow** - Payment escrow and release
- **ReputationToken** - Reputation tracking

See `/contracts` folder for contract source code and ABIs.
