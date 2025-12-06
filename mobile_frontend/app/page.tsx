'use client';

import { VoiceAgent } from '../src/components/VoiceAgent';
import { JobFeed } from '../src/components/JobFeed';
import { WalletConnectPanel } from '../src/features/wallet/WalletConnectPanel';
import './globals.css';

export default function HomePage() {
  const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;
  const spoonosButlerUrl = process.env.NEXT_PUBLIC_SPOONOS_BUTLER_URL || 'http://localhost:3001/api/spoonos';

  const handleSpoonosMessage = (message: any) => {
    console.log('📨 Received from Spoonos Butler:', message);
    // You can update UI state here based on butler responses
  };

  return (
    <main className="app-root">
      <section className="sphere-section">
        <VoiceAgent 
          agentId={agentId}
          spoonosButlerUrl={spoonosButlerUrl}
          onSpoonosMessage={handleSpoonosMessage}
        />
      </section>
      <section className="feed-section">
        <JobFeed />
      </section>
      <section className="wallet-section">
        <WalletConnectPanel />
      </section>
    </main>
  );
}
