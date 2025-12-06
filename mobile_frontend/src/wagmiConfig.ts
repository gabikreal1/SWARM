import { http, createConfig } from 'wagmi';
import { mainnet } from 'wagmi/chains';

// TODO: replace with real NeoX chain definition
// const neox = { ... } as const;

export const wagmiConfig = createConfig({
  chains: [mainnet],
  transports: {
    [mainnet.id]: http(),
  },
});
