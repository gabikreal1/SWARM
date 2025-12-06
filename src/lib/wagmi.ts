import { http, createConfig } from "wagmi";
import { injected } from "wagmi/connectors";
import type { Chain } from "viem";
import { chainDefaults } from "./contracts";

const chainId = chainDefaults.chainId;
const rpcUrl = chainDefaults.rpcUrl;
const explorer = chainDefaults.blockExplorer;
const chainName = chainDefaults.chainName || "Neo X Testnet";

export const neoXTestnet: Chain = {
  id: chainId,
  name: chainName,
  nativeCurrency: { name: "GAS", symbol: "GAS", decimals: 18 },
  rpcUrls: {
    default: { http: [rpcUrl] },
    public: { http: [rpcUrl] },
  },
  blockExplorers: {
    default: { name: "Explorer", url: explorer },
  },
  testnet: true,
};

export const wagmiConfig = createConfig({
  chains: [neoXTestnet],
  transports: {
    [neoXTestnet.id]: http(rpcUrl),
  },
  connectors: [injected()],
  ssr: true,
});

