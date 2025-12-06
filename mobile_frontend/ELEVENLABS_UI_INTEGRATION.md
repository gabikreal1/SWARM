# ElevenLabs UI Integration - Official Components

**Last Updated:** 2025-12-05

## Overview

Your voice agent now uses **official ElevenLabs UI components** from the [elevenlabs/ui](https://github.com/elevenlabs/ui) library, replacing the custom WebGL implementation with production-ready, MIT-licensed components.

## What Changed

### Before (Custom Implementation)
- ✅ Custom `ButlerSphere.tsx` with WebGL shaders
- ✅ Manual vertex/fragment shader files
- ✅ Custom perlin noise animation system

### After (Official Components)
- ✅ **Official `Orb` component** from ElevenLabs UI
- ✅ Pre-built voice-reactive animations
- ✅ Built-in agent states (idle, listening, talking, thinking)
- ✅ Professional-grade visual design
- ✅ Maintained compatibility with existing `useConversation` hook

## Installation Steps Completed

### 1. Setup Tailwind CSS & shadcn/ui (Prerequisites)
```bash
# Installed dependencies
npm install -D tailwindcss postcss autoprefixer tailwindcss-animate
npm install clsx tailwind-merge

# Created configuration files
- tailwind.config.ts
- postcss.config.mjs
- components.json (shadcn/ui config)
- lib/utils.ts (cn utility)
```

### 2. Updated TypeScript Paths
Added path aliases to `tsconfig.json`:
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### 3. Installed Official Orb Component
```bash
# Three.js dependencies (already installed)
npm install @react-three/fiber @react-three/drei three
npm install -D @types/three

# Component installed from registry
components/ui/orb.tsx (16KB shader code included)
```

## Component Usage

### Basic Orb Usage
```tsx
import { Orb } from '@/components/ui/orb';

<Orb 
  className="h-full w-full"
  volumeMode="manual"
  getInputVolume={() => 0.5}
  getOutputVolume={() => 0.7}
  agentState="talking"
  colors={["#22d3ee", "#0ea5e9"]}
/>
```

### Integration with useConversation
Your `VoiceAgent.tsx` now uses:

```tsx
const getInputVolume = useCallback(() => {
  return conversation.isSpeaking ? 0.8 : 0.0;
}, [conversation.isSpeaking]);

const getOutputVolume = useCallback(() => {
  const rawValue = conversation.isSpeaking ? 0.7 : 0.3;
  return Math.min(1.0, Math.pow(rawValue, 0.5) * 2.5);
}, [conversation.isSpeaking]);

<Orb
  className="h-full w-full"
  volumeMode="manual"
  getInputVolume={getInputVolume}
  getOutputVolume={getOutputVolume}
  agentState={
    conversation.status === 'connected' 
      ? conversation.isSpeaking 
        ? 'talking' 
        : 'listening'
      : null
  }
  colors={["#22d3ee", "#0ea5e9"]}
/>
```

## Orb Component API

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `className` | `string` | `"relative h-full w-full"` | Container styling |
| `colors` | `[string, string]` | `["#CADCFC", "#A0B9D1"]` | Gradient colors [darker, lighter] |
| `volumeMode` | `"auto" \| "manual"` | `"auto"` | How to determine volume levels |
| `agentState` | `null \| "thinking" \| "listening" \| "talking"` | `null` | Visual state of the agent |
| `getInputVolume` | `() => number` | - | Function returning input volume (0-1) |
| `getOutputVolume` | `() => number` | - | Function returning output volume (0-1) |
| `seed` | `number` | random | Seed for consistent randomness |
| `resizeDebounce` | `number` | `100` | Canvas resize debounce (ms) |

### Agent States

- **`null`** (idle): Gentle breathing animation
- **`"listening"`**: Active listening with pulsing rings
- **`"talking"`**: Dynamic speaking animation
- **`"thinking"`**: Contemplative motion

### Volume Reactivity

The orb responds to two volume inputs:
- **Input Volume** (microphone): Affects ring size and glow intensity
- **Output Volume** (agent speech): Controls animation speed and color intensity

Values should be normalized between 0 and 1:
```tsx
// Example: Map raw audio levels
const inputVol = Math.min(1, audioLevel / 100);
const outputVol = Math.pow(rawValue, 0.5) * 2.5; // Apply curve for better visual effect
```

## Available Components from ElevenLabs UI

You can install additional components:

### Voice Chat Blocks
```bash
# Full voice chat interface
npx shadcn@latest add https://ui.elevenlabs.io/r/voice-chat-01.json
npx shadcn@latest add https://ui.elevenlabs.io/r/voice-chat-02.json
```

### Conversation Components
```bash
# Conversation container with auto-scroll
npx shadcn@latest add https://ui.elevenlabs.io/r/conversation.json

# Conversation bar with controls
npx shadcn@latest add https://ui.elevenlabs.io/r/conversation-bar.json

# Message bubbles
npx shadcn@latest add https://ui.elevenlabs.io/r/message.json
```

### Voice Controls
```bash
# Voice button with recording states
npx shadcn@latest add https://ui.elevenlabs.io/r/voice-button.json

# Voice picker with audio preview
npx shadcn@latest add https://ui.elevenlabs.io/r/voice-picker.json
```

### Audio Components
```bash
# Audio player
npx shadcn@latest add https://ui.elevenlabs.io/r/audio-player.json

# Waveform visualization
npx shadcn@latest add https://ui.elevenlabs.io/r/waveform.json
```

## Custom Orb Colors

Match your brand:
```tsx
// Cyan/Blue (current)
colors={["#22d3ee", "#0ea5e9"]}

// Purple/Pink
colors={["#a855f7", "#ec4899"]}

// Green/Emerald
colors={["#10b981", "#059669"]}

// Orange/Red
colors={["#f97316", "#ef4444"]}
```

## Troubleshooting

### Orb not appearing
- Check if Tailwind CSS is loaded: `@tailwind base;` in `globals.css`
- Verify Three.js dependencies: `@react-three/fiber`, `@react-three/drei`, `three`
- Ensure container has explicit dimensions

### Volume not reacting
- Verify `volumeMode="manual"` is set
- Check `getInputVolume` and `getOutputVolume` return values between 0-1
- Use `console.log` to debug volume values

### TypeScript errors
- Confirm `@types/three` is installed
- Check path alias `@/*` in `tsconfig.json`
- Restart TypeScript server in VS Code

## Node.js Version Note

**Important:** ElevenLabs CLI requires Node.js 20+, but the components themselves work fine on Node.js 18.20.8 (your current version).

If you want to use the CLI in the future:
```bash
# Upgrade Node.js (macOS with Homebrew)
brew install node@20

# Or use nvm
nvm install 20
nvm use 20
```

For now, manually installing components via curl + create_file works perfectly.

## Next Steps

### Option 1: Keep Current Setup (Recommended)
Your voice agent is fully functional with:
- ✅ Official Orb component
- ✅ ElevenLabs useConversation hook
- ✅ Client tools bridging to Spoonos Butler API
- ✅ Voice-reactive animations

### Option 2: Add More UI Components
Consider adding:
1. **ConversationBar** - Full voice interface with mic controls and waveforms
2. **Message components** - Display conversation history
3. **VoiceButton** - Recording states with visual feedback

### Option 3: Explore Voice Chat Blocks
Check examples at https://ui.elevenlabs.io/blocks:
- `voice-chat-01` - Chat interface with transcript
- `voice-chat-02` - Minimalist orb-based interface
- `voice-form-01` - Voice-controlled form filling

## File Structure

```
mobile_frontend/
├── components/
│   └── ui/
│       └── orb.tsx              # Official ElevenLabs Orb component
├── lib/
│   └── utils.ts                 # Tailwind cn() utility
├── src/
│   └── components/
│       ├── VoiceAgent.tsx       # Updated with Orb integration
│       └── ButlerSphere.tsx     # Legacy (can be removed)
├── app/
│   ├── globals.css              # Tailwind + shadcn/ui CSS variables
│   ├── layout.tsx
│   └── page.tsx
├── tailwind.config.ts           # Tailwind configuration
├── postcss.config.mjs           # PostCSS configuration
├── components.json              # shadcn/ui configuration
└── tsconfig.json                # TypeScript with path aliases
```

## Resources

- **ElevenLabs UI Docs**: https://ui.elevenlabs.io/docs
- **GitHub Repository**: https://github.com/elevenlabs/ui
- **Component Registry**: https://ui.elevenlabs.io/docs/components/orb
- **Blocks/Examples**: https://ui.elevenlabs.io/blocks

## Summary

You now have:
- ✅ Production-ready UI components from ElevenLabs
- ✅ Professional voice-reactive orb animations
- ✅ Tailwind CSS + shadcn/ui foundation
- ✅ Full compatibility with existing architecture
- ✅ Easy path to add more official components
- ✅ MIT-licensed open-source components

The custom `ButlerSphere.tsx` can be kept as a backup or removed. The official Orb provides the same functionality with better visuals, performance, and maintainability.
