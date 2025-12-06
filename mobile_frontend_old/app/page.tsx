import { ButlerSphere } from '../src/components/ButlerSphere';
import { JobFeed } from '../src/components/JobFeed';
import { WalletConnectPanel } from '../src/features/wallet/WalletConnectPanel';
import './globals.css';

export default function HomePage() {
  return (
    <main className="app-root">
      <section className="sphere-section">
        <ButlerSphere />
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
