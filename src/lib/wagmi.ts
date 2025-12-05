import { http, createConfig } from "wagmi";
import { injected } from "wagmi/connectors";
import type { Chain } from "viem";
import { chainDefaults } from "./contracts";

const chainId = chainDefaults.chainId;
const rpcUrl = chainDefaults.rpcUrl;
const explorer = chainDefaults.blockExplorer;

export const arcTestnet: Chain = {
  id: chainId,
  name: "Arc Testnet",
  nativeCurrency: { name: "GAS", symbol: "GAS", decimals: 18 },
  rpcUrls: {
    default: { http: [rpcUrl] },
    public: { http: [rpcUrl] },
  },
  blockExplorers: {
    default: { name: "ArcScan", url: explorer },
  },
  testnet: true,
};

export const wagmiConfig = createConfig({
  chains: [arcTestnet],
  transports: {
    [arcTestnet.id]: http(rpcUrl),
  },
  connectors: [injected()],
  ssr: true,
});

