export const chainDefaults = {
  // Neo X Testnet (GAS); override via NEXT_PUBLIC_* envs if needed
  chainId: Number(process.env.NEXT_PUBLIC_CHAIN_ID || 12227332),
  agentRegistry: process.env.NEXT_PUBLIC_AGENT_REGISTRY || "",
  orderBook: process.env.NEXT_PUBLIC_ORDER_BOOK || "",
  escrow: process.env.NEXT_PUBLIC_ESCROW || "",
  jobRegistry: process.env.NEXT_PUBLIC_JOB_REGISTRY || "",
  reputationToken: process.env.NEXT_PUBLIC_REPUTATION_TOKEN || "",
  usdc: process.env.NEXT_PUBLIC_USDC || "",
  rpcUrl:
    process.env.NEXT_PUBLIC_RPC_URL ||
    "https://neoxt4seed1.ngd.network",
  blockExplorer:
    process.env.NEXT_PUBLIC_BLOCK_EXPLORER ||
    "https://xt4scan.ngd.network",
  chainName:
    process.env.NEXT_PUBLIC_CHAIN_NAME ||
    "Neo X Testnet",
};

