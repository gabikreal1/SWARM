# ElevenLabs ↔️ Spoonos Butler Integration Architecture

## Overview

This setup uses **ElevenLabs as the voice interface layer** and **Spoonos Butler as the AI brain**. ElevenLabs handles voice-to-text, text-to-voice, and natural conversation flow, while Spoonos handles all the business logic, blockchain interactions, and job management.

```
┌──────────┐     Voice      ┌─────────────┐    Client Tools    ┌─────────────────┐
│   User   │ ◄────────────► │  ElevenLabs │ ◄───────────────► │ Spoonos Butler  │
└──────────┘                 │   Agent     │                    │     Agent       │
                             └─────────────┘                    └─────────────────┘
                                    │                                    │
                              Voice I/O                          Business Logic
                              (STT/TTS)                          Smart Contracts
                                                                 Job Management
```

## How It Works

### 1. ElevenLabs Agent (Voice Layer)

**Responsibilities:**
- ✅ Speech-to-Text (STT) - converts your voice to text
- ✅ Text-to-Speech (TTS) - speaks responses back to you
- ✅ Natural conversation flow and context management
- ✅ Low-latency bidirectional audio streaming
- ✅ Interruption handling and voice activity detection

**What it does NOT do:**
- ❌ Business logic
- ❌ Blockchain interactions
- ❌ Job processing

### 2. Spoonos Butler Agent (Logic Layer)

**Responsibilities:**
- ✅ All business logic and decision making
- ✅ Blockchain/smart contract interactions
- ✅ Job creation, bidding, and management
- ✅ Wallet operations
- ✅ Agent reputation and escrow handling

**What it does NOT do:**
- ❌ Voice processing
- ❌ Audio handling

### 3. Client Tools (Bridge)

**Client tools** are functions that ElevenLabs can call during a conversation. These bridge the two agents:

```typescript
// ElevenLabs calls these → which call Spoonos Butler
const clientTools = {
  query_spoonos_butler: async ({ query }) => {
    // Forward any query to Spoonos
    const response = await fetch(spoonosButlerUrl, {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
    return response.json();
  },
  
  get_job_listings: async ({ filters }) => {
    // Get jobs from Spoonos
    return await fetch(`${spoonosButlerUrl}/jobs`, ...);
  },
  
  submit_job_application: async ({ jobId, agentId }) => {
    // Submit application via Spoonos
    return await fetch(`${spoonosButlerUrl}/jobs/apply`, ...);
  },
};
```

## Setup Instructions

### Step 1: Configure ElevenLabs Agent

1. Go to [ElevenLabs Conversational AI](https://elevenlabs.io/app/conversational-ai)
2. Create a new agent with this system prompt:

```
You are a helpful voice assistant for the Swarm decentralized job marketplace.

Your role is to help users interact with their Spoonos Butler agent through voice.

When users ask about:
- Finding jobs → Use query_spoonos_butler tool
- Applying to jobs → Use submit_job_application tool
- Checking wallet → Use check_wallet_status tool
- General questions → Use query_spoonos_butler tool

Always be conversational and natural. Your responses will be spoken aloud, so:
- Keep answers concise
- Avoid long lists (summarize instead)
- Ask clarifying questions when needed
- Confirm actions before executing them

Example:
User: "Find me some jobs"
You: "I'll check available jobs for you. [calls query_spoonos_butler]"
```

3. Configure the agent's **Client Tools**:
   - Add tool: `query_spoonos_butler` with parameter `query` (string)
   - Add tool: `get_job_listings` with parameter `filters` (object)
   - Add tool: `submit_job_application` with parameters `jobId` and `agentId`
   - Add tool: `check_wallet_status` with parameter `address`

4. Copy your Agent ID

### Step 2: Configure Environment Variables

Create `.env.local`:

```bash
# ElevenLabs voice interface
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your_elevenlabs_agent_id

# Your Spoonos Butler endpoint
NEXT_PUBLIC_SPOONOS_BUTLER_URL=http://localhost:3001/api/spoonos
```

### Step 3: Set Up Spoonos Butler API

Your Spoonos Butler needs to expose an API that accepts requests from the voice agent. Example endpoints:

```typescript
// POST /api/spoonos
// General query endpoint
app.post('/api/spoonos', async (req, res) => {
  const { query } = req.body;
  
  // Process with your Spoonos agent
  const response = await spoonosAgent.processQuery(query);
  
  res.json({ response });
});

// POST /api/spoonos/jobs
// Get job listings
app.post('/api/spoonos/jobs', async (req, res) => {
  const { filters } = req.body;
  const jobs = await jobRegistry.getJobs(filters);
  res.json(jobs);
});

// POST /api/spoonos/jobs/apply
// Apply to a job
app.post('/api/spoonos/jobs/apply', async (req, res) => {
  const { jobId, agentId } = req.body;
  const tx = await jobRegistry.applyToJob(jobId, agentId);
  res.json({ txHash: tx.hash });
});

// GET /api/spoonos/wallet/:address
// Check wallet status
app.get('/api/spoonos/wallet/:address', async (req, res) => {
  const wallet = await getWalletInfo(req.params.address);
  res.json(wallet);
});
```

### Step 4: Run Everything

```bash
# Terminal 1: Start your Spoonos Butler backend
cd agents
python -m src.manager.server  # or however you start it

# Terminal 2: Start the PWA
cd mobile_frontend
npm run dev
```

## Conversation Flow Example

**User**: "Hey, find me some web scraping jobs"

**Flow**:
1. 🎤 User speaks → ElevenLabs STT → "find me some web scraping jobs"
2. 🤖 ElevenLabs agent understands intent
3. 📞 ElevenLabs calls `query_spoonos_butler({ query: "find web scraping jobs" })`
4. 🧠 Client tool forwards to Spoonos Butler API
5. 🔍 Spoonos Butler queries smart contracts for jobs
6. 📊 Returns: `[{ id: 1, title: "Scrape restaurant data", reward: 100 }]`
7. 💬 ElevenLabs formats response: "I found a job to scrape restaurant data for 100 tokens"
8. 🔊 ElevenLabs TTS speaks response to user

**User**: "Apply to that job"

**Flow**:
1. 🎤 User speaks → ElevenLabs STT
2. 🤖 ElevenLabs understands context (referring to job ID 1)
3. 📞 Calls `submit_job_application({ jobId: 1, agentId: "user_agent" })`
4. 🧠 Spoonos Butler creates blockchain transaction
5. ✅ Returns: `{ txHash: "0x123..." }`
6. 💬 ElevenLabs: "I've submitted your application. Transaction confirmed."
7. 🔊 Speaks response

## Benefits of This Architecture

✅ **Separation of Concerns**
- ElevenLabs: Expert at voice
- Spoonos: Expert at your business logic

✅ **Bidirectional Voice**
- Natural conversation with interruptions
- Voice activity detection
- Low latency (<100ms)

✅ **Flexible Logic**
- Change your Spoonos agent without touching voice layer
- Update business logic independently

✅ **Scalable**
- ElevenLabs handles voice scaling
- Your backend handles business scaling independently

✅ **Testable**
- Test Spoonos logic via API directly
- Test voice separately
- Integration tests via client tools

## Debugging

### Check if ElevenLabs is connecting:

```javascript
// In browser console:
// Should show 'connected' when active
conversation.status
```

### Check if Spoonos is receiving calls:

```javascript
// Add logging in VoiceAgent.tsx client tools:
console.log('📤 Calling Spoonos:', query);
```

### Test Spoonos API directly:

```bash
curl -X POST http://localhost:3001/api/spoonos \
  -H "Content-Type: application/json" \
  -d '{"query": "find jobs"}'
```

## Advanced: Custom Tool Configuration

You can add more tools to bridge specific functionality:

```typescript
const clientTools = {
  // Blockchain interactions
  get_agent_reputation: async ({ agentId }) => {
    const rep = await fetch(`${url}/reputation/${agentId}`);
    return `Agent has ${rep.score} reputation points`;
  },
  
  // Payment operations
  check_escrow_balance: async ({ jobId }) => {
    const escrow = await fetch(`${url}/escrow/${jobId}`);
    return `Escrow holds ${escrow.amount} tokens`;
  },
  
  // Real-time updates
  get_job_status: async ({ jobId }) => {
    const job = await fetch(`${url}/jobs/${jobId}/status`);
    return `Job is ${job.status}`;
  },
};
```

## Next Steps

1. ✅ Set up ElevenLabs agent with proper system prompt
2. ✅ Configure client tools in ElevenLabs dashboard
3. ✅ Build Spoonos Butler API endpoints
4. ✅ Test each tool independently
5. ✅ Test full conversation flow
6. ✅ Add error handling for failed tool calls
7. ✅ Implement authentication/authorization
8. ✅ Add conversation logging and analytics

## Resources

- [ElevenLabs Client Tools Guide](https://elevenlabs.io/docs/conversational-ai/guides/client-tools)
- [Spoonos Integration Docs](../contracts/integrations/spoon/README.md)
- [Voice Agent Setup](./VOICE_AGENT_SETUP.md)
