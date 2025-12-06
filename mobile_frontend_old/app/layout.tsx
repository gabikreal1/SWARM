import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Swarm Butler',
  description: 'Decentralized agent Butler PWA on NeoX/NeoFS',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
