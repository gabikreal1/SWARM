import React from 'react';
import { ButlerSphere } from './components/ButlerSphere';
import { JobFeed } from './components/JobFeed';
import { WalletConnectPanel } from './features/wallet/WalletConnectPanel';

export const App: React.FC = () => {
  return (
    <div className="app-root">
      <div className="sphere-section">
        <ButlerSphere />
      </div>
      <div className="feed-section">
        <JobFeed />
      </div>
      <div className="wallet-section">
        <WalletConnectPanel />
      </div>
    </div>
  );
};
