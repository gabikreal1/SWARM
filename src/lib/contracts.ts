export const chainDefaults = {
  // Neo X Testnet (GAS); override via NEXT_PUBLIC_* envs if needed
  chainId: Number(process.env.NEXT_PUBLIC_CHAIN_ID || 12227332),
  agentRegistry:
    process.env.NEXT_PUBLIC_AGENT_REGISTRY ||
    "0xbf76cEc97DDE6EC8b62e89e37C8B020a632ec4Df",
  orderBook:
    process.env.NEXT_PUBLIC_ORDER_BOOK ||
    "0xF86e4A9608aF5A08c037925FEe3C65BCDa12e465",
  escrow:
    process.env.NEXT_PUBLIC_ESCROW ||
    "0x6C658B4077DD29303ec1bDafb43Db571d4F310c8",
  jobRegistry:
    process.env.NEXT_PUBLIC_JOB_REGISTRY ||
    "0xd6aac3B6D997Be956f0d437732fea2e9a6927189",
  reputationToken:
    process.env.NEXT_PUBLIC_REPUTATION_TOKEN ||
    "0x540eBF386dd98EB575B63D1eaC243Db80c455066",
  usdc:
    process.env.NEXT_PUBLIC_USDC ||
    "0x9f1Af8576f52507354eaF2Dc438a5333Baf2D09D",
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

