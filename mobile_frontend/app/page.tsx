"use client";

import { useEffect, useState } from 'react';
import { VoiceAgent } from '../src/components/VoiceAgent';
import { Sidebar } from '../src/components/Sidebar';
import { WelcomeHeading } from '../src/components/WelcomeHeading';
import { WalletConnectButton } from '../src/components/WalletConnectButton';
import { SendToButler } from '../src/components/SendToButler';
import './globals.css';

export default function HomePage() {
  const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID;
  const spoonosButlerUrl = process.env.NEXT_PUBLIC_SPOONOS_BUTLER_URL || 'http://localhost:3001/api/spoonos';

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [conversations] = useState([]);
  const [orbVisible, setOrbVisible] = useState(false);
  const [ctaVisible, setCtaVisible] = useState(false);
  const [chatReady, setChatReady] = useState(false);

  useEffect(() => {
    const headerDuration = 900;
    const orbDelay = 200;
    const ctaDelay = 600;
    const chatDelay = 800;

    const t1 = setTimeout(() => setOrbVisible(true), headerDuration + orbDelay);
    const t2 = setTimeout(() => setCtaVisible(true), headerDuration + ctaDelay);
    const t3 = setTimeout(() => setChatReady(true), headerDuration + chatDelay);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  const handleSpoonosMessage = (message: any) => {
    console.log('📨 Received from Spoonos Butler:', message);
    // You can update UI state here based on butler responses
  };

  return (
    <main className="flex flex-col h-screen px-3 sm:px-4 pt-4 sm:pt-5">
    <header className="app-header flex-none">
        <button
          className="icon-button header-icon"
          aria-label="Open menu"
          type="button"
          onClick={() => setIsSidebarOpen(true)}
        >
          ☰
        </button>
        <div className="app-header-spacer" />
          <div className="flex items-center gap-3 sm:gap-4">
            <WalletConnectButton />
          </div>
      </header>

      <div className="send-card-wrapper">
        <SendToButler />
      </div>

      <section className="sphere-section flex-1 flex flex-col overflow-hidden">
        <div className="flex flex-col flex-1 overflow-hidden">
        <div className="flex flex-col items-center flex-none pb-4">
          <div className="welcome-anim">
            <WelcomeHeading />
          </div>
        </div>

        {/* VoiceAgent contains flex-1 scrollable chat and bottom mic */}
        <div className="flex-1 min-h-0">
          <VoiceAgent 
            agentId={agentId}
            spoonosButlerUrl={spoonosButlerUrl}
            onSpoonosMessage={handleSpoonosMessage}
            sidebarOpen={isSidebarOpen}
            orbVisible={orbVisible}
            ctaVisible={ctaVisible}
            chatReady={chatReady}
          />
        </div>
        </div>
      </section>
      <Sidebar
        open={isSidebarOpen}
        conversations={conversations}
        onSelect={() => setIsSidebarOpen(false)}
        onClose={() => setIsSidebarOpen(false)}
      />
    </main>
  );
}
