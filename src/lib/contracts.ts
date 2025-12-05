export const chainDefaults = {
  chainId: Number(process.env.NEXT_PUBLIC_CHAIN_ID || 5042002),
  agentRegistry:
    process.env.NEXT_PUBLIC_AGENT_REGISTRY ||
    "0x5a498B16049eb12A7DFF16f8fD94F94CD86466dB",
  orderBook:
    process.env.NEXT_PUBLIC_ORDER_BOOK ||
    "0xE345603d32AC0584336b9efFeF8BBEE28Ec2A34e",
  escrow:
    process.env.NEXT_PUBLIC_ESCROW ||
    "0x371cAb74d5Eaf35A4bc81dC1B444267F0debDf58",
  jobRegistry:
    process.env.NEXT_PUBLIC_JOB_REGISTRY ||
    "0x9c7989cAbF4d6DB39844c185BE25922448D2b60F",
  reputationToken:
    process.env.NEXT_PUBLIC_REPUTATION_TOKEN ||
    "0xe8E554AD957734AF1C5d3411E45b1596bBf2AE6D",
  usdc:
    process.env.NEXT_PUBLIC_USDC ||
    "0x3600000000000000000000000000000000000000",
  rpcUrl:
    process.env.NEXT_PUBLIC_RPC_URL ||
    "https://arc-testnet.xenonlabs.net/rpc",
  blockExplorer:
    process.env.NEXT_PUBLIC_BLOCK_EXPLORER ||
    "https://arc-explorer.xenonlabs.net",
};

