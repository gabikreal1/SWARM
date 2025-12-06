import { http, createConfig } from 'wagmi';
import { injected, metaMask, coinbaseWallet, walletConnect } from 'wagmi/connectors';
import { mainnet } from 'wagmi/chains';

// TODO: replace with real NeoX chain definition
// const neox = { ... } as const;

export const wagmiConfig = createConfig({
  chains: [mainnet],
  transports: {
    [mainnet.id]: http(),
  },
  connectors: [
    injected({ shimDisconnect: true }),
    metaMask({ shimDisconnect: true }),
    coinbaseWallet({ appName: 'Swarm Butler' }),
    walletConnect({
      projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '',
      metadata: {
        name: 'Swarm Butler',
        description: 'Voice + agent chat dapp',
        url: 'https://example.com',
        icons: ['https://walletconnect.com/walletconnect-logo.png'],
      },
      showQrModal: true,
    }),
  ],
  ssr: true,
});
