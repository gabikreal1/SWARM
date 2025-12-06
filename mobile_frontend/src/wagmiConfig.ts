import { http, createConfig } from 'wagmi';
import { injected, metaMask, coinbaseWallet, walletConnect } from 'wagmi/connectors';

const neoxTestnet = {
  id: 12227332,
  name: 'NeoX Testnet T4',
  nativeCurrency: { name: 'GAS', symbol: 'GAS', decimals: 18 },
  rpcUrls: {
    default: {
      http: [process.env.NEXT_PUBLIC_NEOX_RPC_URL || 'https://testnet.rpc.banelabs.org'],
    },
  },
  blockExplorers: {
    default: {
      name: 'NeoX Testnet Explorer',
      url: 'https://xt4scan.ngd.network',
    },
  },
} as const;

export const wagmiConfig = createConfig({
  chains: [neoxTestnet],
  transports: {
    [neoxTestnet.id]: http(neoxTestnet.rpcUrls.default.http[0]),
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
