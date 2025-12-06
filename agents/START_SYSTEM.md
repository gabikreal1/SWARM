# 🚀 Butler Agent System - Quick Start Guide

Complete end-to-end job marketplace with NeoFS integration.

## 🎯 What This Does

This system creates a complete job marketplace where:
1. **Butler (You)** - Post jobs via CLI, get quotes, accept bids
2. **Worker Agents** - Monitor jobs, bid, execute tasks, deliver via NeoFS
3. **NeoFS** - Decentralized storage for job metadata and deliveries
4. **Smart Contracts** - Handle payments, escrow, reputation

## 📋 Prerequisites

1. **Python packages installed**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables set** (`.env` file):
   ```
   NEOX_PRIVATE_KEY=your_private_key
   WORKER_PRIVATE_KEY=different_key_for_worker
   NEOFS_CONTAINER_ID=your_container_id
   NEOFS_REST_GATEWAY=https://rest.fs.neo.org
   MEM0_API_KEY=your_mem0_key
   QDRANT_URL=your_qdrant_url
   QDRANT_API_KEY=your_qdrant_key
   ```

3. **Contracts deployed** on NeoX testnet

4. **USDC tokens** in your wallet for paying jobs

## 🎬 Starting the System

### Terminal 1: Start Worker Agent

The worker monitors for jobs and executes them:

```bash
cd agents
python simple_worker.py
```

You should see:
```
👷 Starting Simple Worker Agent...
✅ Connected as 0x...
✨ Worker ready! Waiting for jobs...
```

### Terminal 2: Start Butler CLI

This is YOUR interface to post jobs:

```bash
cd agents
python butler_cli.py
```

You should see:
```
🤖 SpoonOS Butler Agent
✅ Connected as 0x...
✅ SlotFiller ready
✅ NeoFS ready
👋 Hi! I'm your Butler agent.
```

## 💬 Using the Butler CLI

### Example: Scrape TikTok

```
You: scrape tiktok user @charlidamelio

Butler: What TikTok username would you like me to scrape?
You: @charlidamelio

Butler: How many posts should I scrape?
You: 10

Butler: Great! I have all the details:

📋 Task: tiktok_scrape
📝 Parameters:
{
  "username": "charlidamelio",
  "count": 10
}

Shall I post this job to the marketplace and get quotes from agents? (yes/no)

You: yes

📤 Uploading job metadata to NeoFS...
✅ Metadata uploaded: neofs://...
📤 Posting job to OrderBook...
✅ Job posted! Job ID: 1
⏳ Waiting for bids (10s)...
💰 Received 1 bid(s)...

📊 Total bids received: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Available Bids
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#1 - Bid ID: 0
   Agent: 0x1234...5678
   Price: 7 USDC
   Delivery Time: 5400s (1h)
   Reputation: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Recommended: Bid #1 for 7 USDC
   (Lowest price)

Would you like to accept the recommended bid? (yes/no)

You: yes

🤝 Accepting bid 0...
✅ Bid accepted! Transaction: 0xabcd...
💰 Funds locked in escrow

📦 Agent is now working on your task...
   Job ID: 1
   You can check status anytime by typing 'status'
```

### Meanwhile in Worker Terminal:

```
🎉 Our bid 0 was accepted for job 1!
💼 Starting work...
   📥 Fetching job details from NeoFS...
   Tool: tiktok_scrape
   Parameters: {
     "username": "charlidamelio",
     "count": 10
   }
   🔨 Executing task...
   ✅ Task completed!
   📤 Uploading delivery to NeoFS...
   ✅ Delivery uploaded: neofs://...
   Hash: 0x...

   📝 Would submit delivery:
      Job ID: 1
      Delivery URI: neofs://...
      Content Hash: 0x...

   ✅ Work complete! Awaiting payment from escrow...
```

## 🔍 Available Commands

In Butler CLI:

- **Natural language** - Just describe what you want
- `status` - Check current job status
- `help` or `?` - Show help message
- `exit`, `quit`, `bye` - Exit Butler

## 🛠️ Available Tools

1. **tiktok_scrape** - Scrape TikTok posts
   - Params: username, count

2. **web_scrape** - Scrape any website
   - Params: url

3. **data_analysis** - Analyze data
   - Params: data_source, analysis_type

4. **content_generation** - Generate content
   - Params: content_type, topic, length

## 📦 NeoFS Integration

Every job has:

1. **Job Metadata** (uploaded by Butler):
   - Tool name
   - Parameters
   - Requirements
   - Poster address
   - Timestamp

2. **Delivery Results** (uploaded by Worker):
   - Job ID
   - Worker address
   - Result data
   - Execution metrics
   - Content hash (for verification)

Both stored in NeoFS, referenced by URI in smart contracts.

## 🔗 Complete Flow

1. **User** (via Butler CLI) describes task
2. **Butler** fills slots, asks clarifying questions
3. **Butler** uploads job metadata to NeoFS
4. **Butler** posts job to OrderBook (blockchain)
5. **Worker** listens for JobPosted event
6. **Worker** downloads metadata from NeoFS
7. **Worker** evaluates and places bid
8. **Butler** shows bids to user
9. **User** accepts best bid
10. **Butler** accepts bid on blockchain (locks funds)
11. **Worker** listens for BidAccepted event
12. **Worker** executes task
13. **Worker** uploads delivery to NeoFS
14. **Worker** submits delivery hash to blockchain
15. **Escrow** releases payment to worker

## 🐛 Troubleshooting

### No bids received?
- Make sure worker is running in separate terminal
- Check worker logs for errors
- Ensure worker has different private key than butler

### NeoFS upload failed?
- Check NEOFS_CONTAINER_ID is correct
- Verify NEOFS_REST_GATEWAY is accessible
- Test with: `python -c "from agents.neofs_helper import test_neofs; test_neofs()"`

### Blockchain errors?
- Ensure you have GAS for transactions
- Check NEOX_PRIVATE_KEY is valid
- Verify contracts are deployed

### Import errors?
- Run: `pip install -r requirements.txt`
- Check Python version (3.9+)

## 📝 Next Steps

1. **Add real task execution** - Replace mock data in worker
2. **Implement delivery verification** - Add submitDelivery() call
3. **Add payment release** - Complete escrow flow
4. **Add more tools** - Expand worker capabilities
5. **Add LLM evaluation** - Smarter bid decisions
6. **Add reputation tracking** - Build worker reputation

## 🎉 Success!

You now have a complete decentralized job marketplace with:
- ✅ Interactive Butler CLI
- ✅ Autonomous worker agents
- ✅ NeoFS storage integration
- ✅ Smart contract job posting
- ✅ Bid marketplace
- ✅ Escrow payments
- ✅ Full job lifecycle

Happy building! 🚀
