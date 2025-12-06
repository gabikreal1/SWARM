import type { Metadata } from 'next';
import './globals.css';
import { ReactNode } from 'react';
import { Providers } from '../src/providers';

export const metadata: Metadata = {
  title: 'Swarm Butler',
  description: 'Decentralized agent Butler PWA on NeoX/NeoFS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
