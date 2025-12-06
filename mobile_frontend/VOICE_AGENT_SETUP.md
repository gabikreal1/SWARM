# 🎙️ Swarm Butler - Voice Agent Setup Guide

## Overview

Your PWA now features a beautiful ElevenLabs-powered voice agent with a ChatGPT-style animated orb that responds to voice interaction in real-time.

## ✨ Features Implemented

✅ **Voice-Reactive Orb** - Beautiful 3D WebGL sphere that pulses with voice input/output  
✅ **ElevenLabs Integration** - Full conversational AI with sub-100ms latency  
✅ **Real-time Status** - Visual feedback showing listening vs speaking states  
✅ **Smooth Animations** - Framer Motion entrance animations  
✅ **PWA Ready** - Works offline and installable as native app  
✅ **TypeScript** - Fully typed for better developer experience  

## 📦 Packages Installed

```json
{
  "@elevenlabs/react": "^0.12.1",      // ElevenLabs React SDK
  "@react-three/drei": "^10.7.7",      // Three.js helpers
  "@react-three/fiber": "^9.4.2",      // React renderer for Three.js
  "framer-motion": "^12.23.25",        // Animation library
  "three": "^0.181.2"                  // 3D graphics library
}
```

## 🚀 Quick Start

### 1. Create Your ElevenLabs Agent

1. Visit [ElevenLabs Voice Lab](https://elevenlabs.io/app/conversational-ai)
2. Click "Create Agent" and configure:
   - **Name**: Swarm Butler (or your preference)
   - **Voice**: Choose from 5000+ voices
   - **Language**: Select from 32+ languages
   - **Personality**: Define your agent's behavior
   - **Knowledge Base**: Upload documents or add context
3. Copy your **Agent ID** from the agent settings page

### 2. Set Environment Variables

Create `.env.local` in the `mobile_frontend` directory:

```bash
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your_agent_id_here
```

**Important**: The `NEXT_PUBLIC_` prefix is required for Next.js to expose the variable to the browser.

### 3. Install Dependencies

```bash
cd mobile_frontend
npm install
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 🎨 Components Architecture

### VoiceAgent.tsx
Main component that manages ElevenLabs conversation lifecycle.

**Key Features:**
- Manages connection state
- Handles microphone permissions
- Provides start/stop controls
- Shows real-time status

**Props:**
```tsx
interface VoiceAgentProps {
  agentId?: string;
  onConversationStart?: (conversationId: string) => void;
  onConversationEnd?: () => void;
}
```

### ButlerSphere.tsx
3D animated orb with WebGL shaders.

**Key Features:**
- Perlin noise-based animations
- Voice-reactive visuals
- Smooth color transitions
- 60fps performance

**Props:**
```tsx
interface ButlerSphereProps {
  conversation?: ReturnType<typeof useConversation>;
}
```

## 🎯 Usage Example

```tsx
import { VoiceAgent } from '../src/components/VoiceAgent';

export default function HomePage() {
  const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;

  return (
    <VoiceAgent 
      agentId={agentId}
      onConversationStart={(id) => {
        console.log('Started conversation:', id);
        // Track analytics, update UI, etc.
      }}
      onConversationEnd={() => {
        console.log('Conversation ended');
        // Clean up, save transcript, etc.
      }}
    />
  );
}
```

## 🎨 Customization

### Change Orb Colors

Edit `src/components/ButlerSphere.tsx`:

```tsx
<OrbScene 
  colors={['#10b981', '#34d399']} // Green gradient
/>
```

Popular color schemes:
- **Cyan/Blue** (default): `['#0ea5e9', '#22d3ee']`
- **Purple**: `['#8b5cf6', '#a78bfa']`
- **Green**: `['#10b981', '#34d399']`
- **Red/Pink**: `['#ef4444', '#f87171']`

### Customize Button Styles

Edit `src/components/VoiceAgent.tsx` - buttons use Tailwind CSS classes:

```tsx
className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
```

### Add Custom Conversation Handlers

```tsx
const conversation = useConversation({
  onMessage: (message) => {
    console.log('Message:', message);
    // Update UI with transcription
  },
  onModeChange: ({ mode }) => {
    console.log('Mode:', mode); // 'speaking' | 'listening'
    // Update visual indicators
  },
  onVolumeChange: ({ inputVolume, outputVolume }) => {
    console.log('Volumes:', inputVolume, outputVolume);
    // Custom volume visualizations
  },
});
```

## 🔧 Advanced Configuration

### Server-Side Signed URL Generation

For production, generate signed URLs on your backend:

```typescript
// pages/api/elevenlabs/signed-url.ts
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const agentId = process.env.ELEVENLABS_AGENT_ID;
  const apiKey = process.env.ELEVENLABS_API_KEY;

  const response = await fetch(
    `https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id=${agentId}`,
    {
      headers: {
        'xi-api-key': apiKey,
      },
    }
  );

  const data = await response.json();
  res.status(200).json(data);
}
```

Then update `VoiceAgent.tsx`:

```typescript
const getSignedUrl = async (): Promise<string> => {
  const response = await fetch('/api/elevenlabs/signed-url');
  const data = await response.json();
  return data.signed_url;
};
```

### Add Dynamic Variables

Pass context to your agent:

```typescript
await conversation.startSession({
  signedUrl,
  dynamicVariables: {
    user_name: userName,
    wallet_address: walletAddress,
    account_balance: balance,
  },
});
```

### Implement Client Tools

Allow your agent to call functions:

```typescript
const conversation = useConversation({
  clientTools: {
    getWalletBalance: async () => {
      const balance = await fetchWalletBalance();
      return `Your balance is ${balance} tokens`;
    },
    submitJob: async (params: { description: string; reward: number }) => {
      const jobId = await createJob(params);
      return `Job created with ID: ${jobId}`;
    },
  },
});
```

## 🐛 Troubleshooting

### Microphone Not Working

**Issue**: Browser can't access microphone  
**Solutions**:
- Ensure HTTPS connection (required for mic access)
- Check browser permissions in settings
- Try different browser (Chrome/Edge recommended)
- On mobile: Allow microphone in app settings

### Orb Not Animating

**Issue**: Sphere appears static or doesn't render  
**Solutions**:
- Check WebGL support: visit [webglreport.com](https://webglreport.com)
- Update graphics drivers
- Disable browser hardware acceleration
- Clear browser cache

### Connection Fails

**Issue**: Can't connect to agent  
**Solutions**:
- Verify `NEXT_PUBLIC_ELEVENLABS_AGENT_ID` is correct
- Check agent is active in ElevenLabs dashboard
- Ensure valid API key (if using server-side auth)
- Check network/firewall settings
- Verify WebSocket connections are allowed

### No Audio Output

**Issue**: Agent connects but no voice heard  
**Solutions**:
- Check system volume and browser audio settings
- Verify correct audio output device selected
- Test with another audio application
- Check for audio codec compatibility

### Build Errors

**Issue**: TypeScript or build errors  
**Solutions**:
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run dev
```

## 📚 Additional Resources

- [ElevenLabs Documentation](https://elevenlabs.io/docs)
- [React SDK Reference](https://github.com/elevenlabs/elevenlabs-react)
- [Conversational AI Guide](https://elevenlabs.io/docs/agents-platform/overview)
- [Three.js Documentation](https://threejs.org/docs)
- [Framer Motion Docs](https://www.framer.com/motion/)

## 🎤 Voice Agent Tips

### Best Practices

1. **Keep prompts clear** - Define agent personality and capabilities precisely
2. **Set boundaries** - Tell the agent what it can and cannot do
3. **Use dynamic variables** - Personalize conversations with user context
4. **Implement tools** - Let agent perform actions via client tools
5. **Handle errors gracefully** - Provide fallback messages for failures

### Example Agent Prompt

```
You are Swarm Butler, a helpful AI assistant for a decentralized job marketplace.

Your capabilities:
- Help users find jobs matching their skills
- Explain how to submit job applications
- Check wallet balances and transaction status
- Answer questions about the Swarm platform

Your personality:
- Professional but friendly
- Clear and concise explanations
- Patient with beginners
- Knowledgeable about blockchain and Web3

If asked to do something you cannot do, politely explain your limitations and suggest alternatives.
```

## 🚀 Next Steps

1. **Customize the orb** - Match your brand colors
2. **Add more client tools** - Connect to your smart contracts
3. **Implement conversation history** - Save and display transcripts
4. **Add multilingual support** - Let users choose their language
5. **Enhance error handling** - Provide better user feedback
6. **Add analytics** - Track conversation metrics
7. **Implement authentication** - Secure conversations with user accounts

## 📝 License

MIT

---

**Need Help?** Check the [ELEVENLABS_INTEGRATION.md](./ELEVENLABS_INTEGRATION.md) file for more details.
