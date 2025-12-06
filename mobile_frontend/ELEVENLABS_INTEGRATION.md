# ElevenLabs Voice Agent Integration

This PWA integrates ElevenLabs Conversational AI with a beautiful animated orb visualization.

## Features

✅ **Voice-reactive orb** - 3D animated sphere that responds to voice input/output  
✅ **Sub-100ms latency** - Real-time conversational AI  
✅ **32+ languages** - Multilingual agent support  
✅ **WebGL visualization** - Smooth 60fps animations  
✅ **PWA-ready** - Works offline and as installable app  

## Setup Instructions

### 1. Create an ElevenLabs Agent

1. Go to [ElevenLabs Voice Lab](https://elevenlabs.io/app/conversational-ai)
2. Create a new Conversational AI agent
3. Configure your agent's voice, personality, and capabilities
4. Copy your **Agent ID** from the settings

### 2. Configure Environment Variables

Create a `.env.local` file in the `mobile_frontend` directory:

```bash
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your_agent_id_here
```

### 3. Install Dependencies

```bash
npm install
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

1. Click **"🎙️ Start Conversation"** to begin talking to your AI agent
2. The orb will animate based on voice input/output
3. Watch the status indicator to see when the agent is listening or speaking
4. Click **"⏹️ End Call"** to stop the conversation

## Components

### VoiceAgent
Main component that manages the ElevenLabs conversation session.

**Props:**
- `agentId` (string) - Your ElevenLabs agent ID
- `onConversationStart` (function) - Callback when conversation starts
- `onConversationEnd` (function) - Callback when conversation ends

### ButlerSphere
Animated 3D orb that reacts to voice input/output using WebGL shaders.

**Props:**
- `conversation` (object) - ElevenLabs conversation hook instance

## Customization

### Change Orb Colors

Edit `src/components/ButlerSphere.tsx`:

```tsx
<OrbScene 
  colors={['#0ea5e9', '#22d3ee']} // Cyan/blue gradient
/>
```

### Add Custom Conversation Logic

Edit `src/components/VoiceAgent.tsx` and add handlers:

```tsx
const conversation = useConversation({
  onMessage: (message) => {
    // Handle incoming messages
    console.log('Received:', message);
  },
  onModeChange: ({ mode }) => {
    // 'speaking' or 'listening'
    console.log('Mode:', mode);
  },
});
```

## Troubleshooting

**Microphone not working:**
- Check browser permissions
- Ensure HTTPS connection (required for microphone access)
- Try a different browser

**Orb not animating:**
- Check WebGL support in your browser
- Update graphics drivers
- Try disabling hardware acceleration

**Connection fails:**
- Verify `NEXT_PUBLIC_ELEVENLABS_AGENT_ID` is set correctly
- Check your internet connection
- Ensure your agent is active in ElevenLabs dashboard

## Resources

- [ElevenLabs Documentation](https://elevenlabs.io/docs)
- [ElevenLabs React SDK](https://github.com/elevenlabs/elevenlabs-react)
- [Conversational AI Platform](https://elevenlabs.io/conversational-ai)

## License

MIT
