# Complete Voice Agent Setup Guide

## Architecture Overview

```
User Voice ↔ ElevenLabs Agent ↔ Frontend Client Tools ↔ Spoonos Butler API ↔ Smart Contracts
   (STT/TTS)      (Conversation)      (Bridge Code)        (Business Logic)      (Blockchain)
```

## Step-by-Step Setup

### Step 1: Start Spoonos Butler API

The API bridge is what ElevenLabs calls to interact with your Spoonos agent.

```bash
cd agents
./start_butler_api.sh
```

This starts an API server at `http://localhost:3001` with endpoints:
- `POST /api/spoonos` - General queries to butler
- `POST /api/spoonos/jobs` - Get job listings
- `POST /api/spoonos/jobs/apply` - Submit applications
- `GET /api/spoonos/wallet/:address` - Check wallet

**Test it works:**
```bash
curl http://localhost:3001/
# Should return: {"status": "Spoonos Butler API is running"}

curl -X POST http://localhost:3001/api/spoonos \
  -H "Content-Type: application/json" \
  -d '{"query": "What jobs are available?"}'
```

### Step 2: Create ElevenLabs Agent

1. Go to https://elevenlabs.io/app/conversational-ai
2. Click "Create Agent"
3. Configure:
   - **Name**: Swarm Butler
   - **Voice**: Choose any voice you like
   - **Language**: English (or your preference)

4. **System Prompt** (paste this):
```
You are a helpful voice assistant for the Swarm decentralized job marketplace.

Your role is to facilitate voice interactions with the Spoonos Butler agent.

AVAILABLE TOOLS:
- query_spoonos_butler: Send any query to the Spoonos Butler AI agent
- get_job_listings: Get available jobs with optional filters
- submit_job_application: Apply to a specific job
- check_wallet_status: Check wallet balance and active jobs

WHEN TO USE TOOLS:
- User asks about jobs → call get_job_listings
- User wants to apply → call submit_job_application (confirm first!)
- User asks about wallet/balance → call check_wallet_status
- Any other question → call query_spoonos_butler

CONVERSATION STYLE:
- Be conversational and natural
- Keep responses concise (they'll be spoken)
- Confirm destructive actions (like spending tokens)
- If a tool fails, explain clearly and suggest alternatives

EXAMPLE:
User: "What jobs are available?"
You: "Let me check the available jobs for you."
[calls get_job_listings]
You: "I found 3 jobs: web scraping for 100 tokens, data analysis for 150 tokens, and API integration for 200 tokens. Which interests you?"
```

5. **Add Client Tools** (in ElevenLabs dashboard):

Click "Add Tool" for each:

**Tool 1:**
- Name: `query_spoonos_butler`
- Description: "Send any general query to the Spoonos Butler AI agent"
- Parameters:
  ```json
  {
    "query": "string (required)"
  }
  ```

**Tool 2:**
- Name: `get_job_listings`  
- Description: "Get list of available jobs from the marketplace"
- Parameters:
  ```json
  {
    "filters": "object (optional)"
  }
  ```

**Tool 3:**
- Name: `submit_job_application`
- Description: "Submit an application to a specific job"
- Parameters:
  ```json
  {
    "jobId": "string (required)",
    "agentId": "string (required)"
  }
  ```

**Tool 4:**
- Name: `check_wallet_status`
- Description: "Check wallet balance and active jobs"
- Parameters:
  ```json
  {
    "address": "string (required)"
  }
  ```

6. **Save** and copy your **Agent ID**

### Step 3: Configure Frontend

Create/update `.env.local`:

```bash
cd mobile_frontend

# Add these variables
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your_agent_id_here
NEXT_PUBLIC_SPOONOS_BUTLER_URL=http://localhost:3001/api/spoonos
```

### Step 4: Start Frontend

```bash
cd mobile_frontend
npm run dev
```

Open http://localhost:3000

## How It Works: Step by Step

### Example Conversation 1: Finding Jobs

**User**: "Show me available jobs"

**What Happens**:
1. 🎤 Your voice is captured by browser
2. 📡 Sent to ElevenLabs voice agent
3. 🤖 ElevenLabs STT converts to text: "Show me available jobs"
4. 🧠 ElevenLabs agent thinks: "User wants jobs, I should call get_job_listings"
5. 📞 ElevenLabs invokes client tool: `get_job_listings({})`
6. 🌐 Frontend `VoiceAgent.tsx` receives the call
7. 📤 Frontend makes HTTP POST to `http://localhost:3001/api/spoonos/jobs`
8. 🔧 Your API (`spoonos_butler_api.py`) processes request
9. 🔍 Queries JobRegistry smart contract
10. 📊 Returns: `[{id: "1", title: "Scrape data", reward: 100}, ...]`
11. 📥 Frontend receives response, returns to ElevenLabs
12. 💬 ElevenLabs formats naturally: "I found 3 jobs. A web scraping task for 100 tokens..."
13. 🔊 ElevenLabs TTS speaks the response
14. 👂 You hear the response

### Example Conversation 2: Applying to Job

**User**: "Apply to the first job"

**What Happens**:
1. 🎤 Voice → ElevenLabs
2. 🤖 ElevenLabs: "User wants to apply, I need jobId"
3. 💬 ElevenLabs: "Just to confirm, you want to apply to the web scraping job for 100 tokens?"
4. 👤 User: "Yes"
5. 📞 ElevenLabs calls: `submit_job_application({jobId: "1", agentId: "user_agent"})`
6. 🌐 Frontend forwards to API
7. 🔧 API creates blockchain transaction
8. ⛓️ Smart contract executes application
9. ✅ Returns transaction hash
10. 💬 ElevenLabs: "Application submitted! Transaction hash is 0x123..."
11. 🔊 Speaks confirmation

## The Code Flow

### Frontend (VoiceAgent.tsx)

```typescript
// This is already in your code
const clientTools = {
  query_spoonos_butler: async ({ query }: { query: string }) => {
    // 1. ElevenLabs calls this function
    console.log('📤 Sending to Spoonos:', query);
    
    // 2. Make HTTP call to your API
    const response = await fetch(spoonosButlerUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    
    // 3. Get response from your API
    const data = await response.json();
    
    // 4. Return to ElevenLabs (it will speak this)
    return data.response;
  },
  // ... other tools
};

// Pass tools to ElevenLabs
const conversation = useConversation({
  clientTools,  // This registers the tools
  // ... other config
});
```

### Backend (spoonos_butler_api.py)

```python
@app.post("/api/spoonos")
async def query_butler(request: QueryRequest):
    # 1. Receive query from frontend
    query = request.query
    
    # 2. Process with your Spoonos agent
    response = await butler_agent.process_query(query)
    
    # 3. Return response (frontend returns this to ElevenLabs)
    return {"response": response}
```

## Testing

### Test 1: API is Running
```bash
curl http://localhost:3001/
```
Expected: `{"status": "Spoonos Butler API is running"}`

### Test 2: Query Butler
```bash
curl -X POST http://localhost:3001/api/spoonos \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello butler"}'
```

### Test 3: Get Jobs
```bash
curl -X POST http://localhost:3001/api/spoonos/jobs \
  -H "Content-Type: application/json" \
  -d '{"filters": {}}'
```

### Test 4: Frontend Connection

1. Start frontend: `npm run dev`
2. Open browser console (F12)
3. Click "Talk to Butler"
4. Say something
5. Check console for:
   - `📤 Sending to Spoonos: ...` (from frontend)
   - `📥 Received query: ...` (from API logs)

## Customization

### Add Your Own Tool

**1. Define in ElevenLabs dashboard:**
```json
{
  "name": "create_new_job",
  "description": "Create a new job posting",
  "parameters": {
    "title": "string",
    "reward": "number",
    "description": "string"
  }
}
```

**2. Add to frontend (VoiceAgent.tsx):**
```typescript
const clientTools = {
  // ... existing tools
  
  create_new_job: async ({ title, reward, description }) => {
    const response = await fetch(`${spoonosButlerUrl}/jobs/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, reward, description }),
    });
    const data = await response.json();
    return `Job created with ID ${data.jobId}`;
  },
};
```

**3. Add to backend (spoonos_butler_api.py):**
```python
@app.post("/api/spoonos/jobs/create")
async def create_job(job: JobCreateRequest):
    # Create job in smart contract
    tx = await job_registry.create_job(
        title=job.title,
        reward=job.reward,
        description=job.description
    )
    return {"jobId": tx.jobId, "txHash": tx.hash}
```

## Troubleshooting

**Issue**: "Failed to get signed URL"
- Solution: Check NEXT_PUBLIC_ELEVENLABS_AGENT_ID is set correctly

**Issue**: "Connection refused to localhost:3001"
- Solution: Make sure Spoonos Butler API is running (`./start_butler_api.sh`)

**Issue**: Tool not being called
- Solution: Check tool name matches exactly between ElevenLabs dashboard and frontend code

**Issue**: No voice response
- Solution: Check browser console for errors, ensure microphone permissions granted

## Production Deployment

For production, you'll need to:

1. **Deploy API** to a server (not localhost)
2. **Update env variables**:
   ```bash
   NEXT_PUBLIC_SPOONOS_BUTLER_URL=https://your-api.com/api/spoonos
   ```
3. **Add authentication** to API endpoints
4. **Enable HTTPS** for microphone access
5. **Add rate limiting** to prevent abuse

## Next Steps

1. ✅ Test basic conversation flow
2. ✅ Integrate with real smart contracts
3. ✅ Add wallet connection
4. ✅ Implement authentication
5. ✅ Add conversation history
6. ✅ Deploy to production
