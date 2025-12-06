"use client";

import React, { useCallback, useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import { Orb } from '@/components/ui/orb';

interface VoiceAgentProps {
  agentId?: string;
  spoonosButlerUrl?: string;
  onSpoonosMessage?: (message: any) => void;
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
  onSpoonosMessage
}) => {
  const [isStarting, setIsStarting] = useState(false);
  const [lastMessage, setLastMessage] = useState<string>('');
  const [volume, setVolume] = useState(1.0);
  
  // Get API key from environment
  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;
  
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
      console.error('❌ Error:', message);
      alert(`Error: ${message}`);
      setIsStarting(false);
    },
    
    onMessage: (message) => {
      console.log('💬 Message:', message);
      if (message.message) {
        setLastMessage(message.message);
      }
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
    <div className="flex flex-col items-center justify-center w-full h-full gap-6">
      {/* Official ElevenLabs UI Orb */}
      <div className="w-40 h-40">
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
      </div>

      {/* Last Message Display */}
      {lastMessage && (
        <div className="max-w-md w-full px-6 py-3 bg-gray-800/50 rounded-lg border border-cyan-500/30">
          <p className="text-xs text-gray-500 mb-1">Spoonos Butler:</p>
          <p className="text-sm text-gray-300">{lastMessage}</p>
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-col items-center gap-4">
        <div className="flex gap-3">
          <button
            onClick={startConversation}
            disabled={!canStart}
            className={`
              px-8 py-3 rounded-full font-semibold text-white
              transition-all duration-300 transform
              ${canStart 
                ? 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 hover:scale-105 shadow-lg hover:shadow-xl' 
                : 'bg-gray-400 cursor-not-allowed opacity-50'
              }
            `}
          >
            {isStarting ? '🔄 Starting...' : '🎙️ Talk to Butler'}
          </button>

          <button
            onClick={stopConversation}
            disabled={!canStop}
            className={`
              px-8 py-3 rounded-full font-semibold text-white
              transition-all duration-300 transform
              ${canStop 
                ? 'bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 hover:scale-105 shadow-lg hover:shadow-xl' 
                : 'bg-gray-400 cursor-not-allowed opacity-50'
              }
            `}
          >
            ⏹️ End Call
          </button>
        </div>

        {/* Volume Control */}
        {conversation.status === 'connected' && (
          <div className="flex items-center gap-3 text-sm text-gray-400">
            <span>🔊 Volume:</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={(e) => {
                const newVolume = parseFloat(e.target.value);
                setVolume(newVolume);
                conversation.setVolume({ volume: newVolume });
              }}
              className="w-32"
            />
            <span>{Math.round(volume * 100)}%</span>
          </div>
        )}

        {/* Status */}
        <div className="text-sm text-gray-400 flex items-center gap-2">
          <div className={`
            w-2 h-2 rounded-full transition-colors
            ${conversation.status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}
          `} />
          <span className="capitalize">
            {conversation.status === 'connected' 
              ? (conversation.isSpeaking ? '🎤 Butler Speaking' : '👂 Listening...') 
              : 'Ready'
            }
          </span>
        </div>

        {/* Instructions */}
        <div className="text-xs text-gray-500 text-center max-w-md">
          ElevenLabs handles voice ↔️ Spoonos Butler handles logic
        </div>

        {!agentId && (
          <div className="text-xs text-yellow-500 bg-yellow-500/10 px-4 py-2 rounded-lg">
            ⚠️ Set NEXT_PUBLIC_ELEVENLABS_AGENT_ID to enable voice
          </div>
        )}
      </div>
    </div>
  );
};
