"use client";

import React, { useCallback, useState } from 'react';

const SplitText: React.FC<{ text: string; className?: string; interval?: number }> = ({ text, className, interval = 60 }) => {
  const words = text.split(' ');
  return (
    <span className={className} aria-label={text} style={{ whiteSpace: 'nowrap' }}>
      {words.map((word, idx) => (
        <span
          key={`${word}-${idx}`}
          style={{
            display: 'inline-block',
            animation: `fadeInChar 0.4s ease forwards`,
            animationDelay: `${idx * interval}ms`,
            opacity: 0,
            marginRight: idx === words.length - 1 ? 0 : '0.25rem',
          }}
        >
          {word}
        </span>
      ))}
    </span>
  );
};
import { useConversation } from '@elevenlabs/react';
import { Orb } from '@/components/ui/orb';
import { ChatTimeline, ChatMessage } from './ChatTimeline';
import { ShinyText } from './ShinyText';

interface VoiceAgentProps {
  agentId?: string;
  spoonosButlerUrl?: string;
  onSpoonosMessage?: (message: any) => void;
  sidebarOpen?: boolean;
  orbVisible?: boolean;
  ctaVisible?: boolean;
  chatReady?: boolean;
}

// Client tools that bridge ElevenLabs to Spoonos Butler
const createSpoonosTools = (spoonosButlerUrl: string, onMessage?: (msg: any) => void) => ({
  // Send user query to Spoonos Butler and get response
  query_spoonos_butler: async ({ query }: { query: string }) => {
    console.log('📤 Sending to Spoonos Butler:', query);
    
    try {
      const response = await fetch(spoonosButlerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, timestamp: Date.now() }),
      });
      
      if (!response.ok) {
        throw new Error(`Spoonos Butler error: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('✅ Spoonos Butler response:', data);
      
      onMessage?.(data);
      
      return data.response || data.message || 'Request processed';
    } catch (error) {
      console.error('❌ Spoonos Butler error:', error);
      return `I had trouble connecting to the butler agent. ${error}`;
    }
  },

  // Get job listings from Spoonos
  get_job_listings: async ({ filters }: { filters?: any }) => {
    console.log('📋 Fetching jobs from Spoonos:', filters);
    
    try {
      const response = await fetch(`${spoonosButlerUrl}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters }),
      });
      
      const jobs = await response.json();
      return `Found ${jobs.length} jobs: ${JSON.stringify(jobs)}`;
    } catch (error) {
      return `Error fetching jobs: ${error}`;
    }
  },

  // Submit job application
  submit_job_application: async ({ jobId, agentId }: { jobId: string; agentId: string }) => {
    console.log('📝 Submitting job application:', { jobId, agentId });
    
    try {
      const response = await fetch(`${spoonosButlerUrl}/jobs/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobId, agentId }),
      });
      
      const result = await response.json();
      return `Application submitted successfully. Transaction: ${result.txHash}`;
    } catch (error) {
      return `Error submitting application: ${error}`;
    }
  },

  // Get wallet status
  check_wallet_status: async ({ address }: { address: string }) => {
    console.log('💼 Checking wallet:', address);
    
    try {
      const response = await fetch(`${spoonosButlerUrl}/wallet/${address}`);
      const wallet = await response.json();
      return `Balance: ${wallet.balance} tokens. Active jobs: ${wallet.activeJobs}`;
    } catch (error) {
      return `Error checking wallet: ${error}`;
    }
  },
});

export const VoiceAgent: React.FC<VoiceAgentProps> = ({ 
  agentId,
  spoonosButlerUrl = 'http://localhost:3001/api/spoonos',
  onSpoonosMessage,
  sidebarOpen = false,
  orbVisible = true,
  ctaVisible = true,
  chatReady = true,
}) => {
  const [isStarting, setIsStarting] = useState(false);
  const [lastMessage, setLastMessage] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [volume, setVolume] = useState(1.0);
  const [hasStarted, setHasStarted] = useState(false);
  
  // Get API key from environment
  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;
  
  const formatError = (err: any) => {
    if (err instanceof Error) return err.message;
    if (typeof err === 'string') return err;
    try {
      return JSON.stringify(err);
    } catch {
      return String(err);
    }
  };

  const conversation = useConversation({
    clientTools: createSpoonosTools(spoonosButlerUrl, onSpoonosMessage),
    
    onConnect: ({ conversationId }) => {
      console.log('✅ Connected to ElevenLabs:', conversationId);
      console.log('🔗 Bridging to Spoonos Butler at:', spoonosButlerUrl);
      console.log('🔊 Audio output should be enabled - check browser volume!');
      
      // Ensure volume is set
      conversation.setVolume({ volume });
    },
    
    onDisconnect: () => {
      console.log('❌ Disconnected from ElevenLabs');
    },
    
    onError: (message) => {
      const text = formatError(message);
      console.error('❌ Error:', message);
      alert(`Error: ${text}`);
      setIsStarting(false);
    },
    
    onMessage: (message) => {
      console.log('💬 Message:', message);
      const text = typeof message.message === 'string' ? message.message : '';
      if (!text) return;

      const incomingRoleRaw = (message.role || message.source || 'assistant').toString().toLowerCase();
      const normalizedRole: ChatMessage['role'] =
        incomingRoleRaw === 'user'
          ? 'user'
          : incomingRoleRaw === 'assistant' || incomingRoleRaw === 'system'
            ? (incomingRoleRaw as ChatMessage['role'])
            : 'assistant';
      const isTranscribed = normalizedRole === 'user';

      setLastMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${prev.length}`,
          role: normalizedRole,
          text,
          isTranscribed,
        },
      ]);
    },
    
    onModeChange: ({ mode }) => {
      console.log(`🔊 Mode: ${mode}`);
    },
  });

  const getSignedUrl = async (): Promise<string> => {
    if (!apiKey) {
      throw new Error('NEXT_PUBLIC_ELEVENLABS_API_KEY not found in environment variables');
    }

    const response = await fetch(
      `https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id=${agentId}`,
      {
        method: 'GET',
        headers: {
          'xi-api-key': apiKey,
        },
      }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to get signed URL: ${response.status} ${errorText}`);
    }
    
    const data = await response.json();
    return data.signed_url;
  };

  const startConversation = useCallback(async () => {
    if (!agentId) {
      alert('Please set NEXT_PUBLIC_ELEVENLABS_AGENT_ID in your environment variables');
      return;
    }
    
    if (!apiKey) {
      alert('Please set NEXT_PUBLIC_ELEVENLABS_API_KEY in your environment variables');
      return;
    }

    setIsStarting(true);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      const signedUrl = await getSignedUrl();
      
      await conversation.startSession({
        signedUrl,
      });
      
      // Set volume after session starts
      setTimeout(() => {
        conversation.setVolume({ volume });
        console.log('🔊 Volume set to:', volume);
      }, 100);

      setHasStarted(true);
    } catch (error) {
      console.error('Failed to start conversation:', error);
      alert('Failed to start conversation. Please check microphone permissions and agent ID.');
    } finally {
      setIsStarting(false);
    }
  }, [conversation, agentId]);

  const stopConversation = useCallback(async () => {
    await conversation.endSession();
  }, [conversation]);

  const canStart = conversation.status === 'disconnected' && !isStarting;
  const canStop = conversation.status === 'connected';

  // Volume tracking for orb animation
  const getInputVolume = useCallback(() => {
    return conversation.isSpeaking ? 0.8 : 0.0;
  }, [conversation.isSpeaking]);

  const getOutputVolume = useCallback(() => {
    const rawValue = conversation.isSpeaking ? 0.7 : 0.3;
    return Math.min(1.0, Math.pow(rawValue, 0.5) * 2.5);
  }, [conversation.isSpeaking]);

  return (
  <div className="flex flex-col w-full h-full min-h-0 pt-2">
    {/* Chat segment: fills between header and sphere, scrollable */}
    <div className="chat-area flex-1 min-h-0 overflow-y-auto px-10 pt-6 pb-12 mb-80 max-w-4xl w-full mx-auto">
    {hasStarted && chatReady && (
      <ChatTimeline messages={messages} />
    )}
    </div>

    {/* Official ElevenLabs UI Orb with mic control, docked near bottom */}
      <div className={`voice-agent-orb-container ${sidebarOpen ? 'orb-shifted' : ''} ${orbVisible ? 'orb-enter-active' : 'orb-enter'}`}>
        {!hasStarted && ctaVisible && (
          <button
            type="button"
            onClick={canStart ? startConversation : undefined}
            className="orb-prompt orb-cta-fade"
            disabled={!canStart}
          >
            <SplitText
              text="Press here to start your conversation"
              className="orb-prompt-text"
              interval={12}
            />
          </button>
        )}
        <div className="relative h-28 w-28 flex items-center justify-center">
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

          <button
            type="button"
            onClick={conversation.status === 'connected' ? stopConversation : startConversation}
            disabled={conversation.status === 'connected' ? !canStop : !canStart}
            className={`mic-button absolute inset-0 m-auto ${
              conversation.status === 'connected'
                ? 'mic-button-active'
                : ''
            } ${
              (!canStart && conversation.status !== 'connected') || (!canStop && conversation.status === 'connected')
                ? 'opacity-50 cursor-not-allowed'
                : ''
            }`}
          >
            <span className="mic-icon" />
          </button>
        </div>

        {/* Status label directly under the sphere */}
        <div className="mt-2 text-xs text-gray-300 text-center w-full">
          {conversation.status === 'connected' && (
            conversation.isSpeaking ? 'Speaking...' : 'Listening...'
          )}
        </div>
      </div>

      {/* Controls (warnings etc.) */}
      <div className="flex flex-col items-center gap-2 mt-2">
        {!agentId && (
          <div className="text-xs text-yellow-500 bg-yellow-500/10 px-4 py-2 rounded-lg">
            ⚠️ Set NEXT_PUBLIC_ELEVENLABS_AGENT_ID to enable voice
          </div>
        )}
      </div>
    </div>
  );
};
