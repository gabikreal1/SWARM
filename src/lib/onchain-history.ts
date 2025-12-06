import { createPublicClient, decodeEventLog, formatUnits, http } from "viem";
import { chainDefaults } from "@/lib/contracts";
import { orderBookAbi } from "@/lib/abi/orderBook";

type OrderBookEvent =
  | {
      type: "JobPosted";
      jobId: bigint;
      poster: `0x${string}`;
    }
  | {
      type: "BidPlaced";
      jobId: bigint;
      bidId: bigint;
      bidder: `0x${string}`;
      price: bigint;
    }
  | {
      type: "BidAccepted";
      jobId: bigint;
      bidId: bigint;
      poster: `0x${string}`;
      agent: `0x${string}`;
    };

export type OnchainEvent = {
  id: string;
  type: OrderBookEvent["type"];
  title: string;
  amount: number;
  wallet: string;
  txHash: string;
  network: string;
  createdAt: string;
};

const orderBookEventAbi = [
  {
    type: "event",
    name: "JobPosted",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "poster", type: "address", indexed: true },
    ],
  },
  {
    type: "event",
    name: "BidPlaced",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "bidId", type: "uint256", indexed: true },
      { name: "bidder", type: "address", indexed: false },
      { name: "price", type: "uint256", indexed: false },
    ],
  },
  {
    type: "event",
    name: "BidAccepted",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "bidId", type: "uint256", indexed: true },
      { name: "poster", type: "address", indexed: false },
      { name: "agent", type: "address", indexed: false },
    ],
  },
] as const;

const ENV_FROM_BLOCK = process.env.NEXT_PUBLIC_ONCHAIN_FROM_BLOCK
  ? BigInt(process.env.NEXT_PUBLIC_ONCHAIN_FROM_BLOCK)
  : null;
const DEFAULT_LOOKBACK = BigInt(
  process.env.NEXT_PUBLIC_ONCHAIN_LOOKBACK || 50000,
);

export async function fetchOrderBookEvents() {
  if (!chainDefaults.orderBook) {
    return [];
  }

  const client = createPublicClient({
    transport: http(chainDefaults.rpcUrl),
    chain: {
      id: chainDefaults.chainId,
      name: chainDefaults.chainName,
      nativeCurrency: { name: "GAS", symbol: "GAS", decimals: 18 },
      rpcUrls: { default: { http: [chainDefaults.rpcUrl] } },
    },
  });

  const latestBlock = await client.getBlockNumber();
  const fromBlock =
    ENV_FROM_BLOCK ??
    (latestBlock > DEFAULT_LOOKBACK ? latestBlock - DEFAULT_LOOKBACK : 0n);

  const logs = await client.getLogs({
    address: chainDefaults.orderBook as `0x${string}`,
    fromBlock,
    toBlock: latestBlock,
  });

  // Prefetch block timestamps
  const blockNumbers = Array.from(new Set(logs.map((l) => l.blockNumber)));
  const blockMap = new Map<bigint, bigint>();
  const blocks = await Promise.all(
    blockNumbers.map((bn) => client.getBlock({ blockNumber: bn }))
  );
  blocks.forEach((b) => blockMap.set(b.number, b.timestamp));

  const decoded: OnchainEvent[] = [];

  for (const log of logs) {
    try {
      const parsed = decodeEventLog({
        abi: orderBookEventAbi,
        data: log.data,
        topics: log.topics,
      });
      const ts = blockMap.get(log.blockNumber) ?? 0n;
      const base = {
        txHash: log.transactionHash || "",
        network: chainDefaults.chainName,
        createdAt: new Date(Number(ts) * 1000).toISOString(),
      };
      if (parsed.eventName === "JobPosted") {
        const { jobId, poster } = parsed.args as {
          jobId: bigint;
          poster: `0x${string}`;
        };
        decoded.push({
          id: `${log.transactionHash}-job-${jobId}`,
          type: "JobPosted",
          title: `Job #${jobId.toString()} posted`,
          amount: 0,
          wallet: poster,
          ...base,
        });
      } else if (parsed.eventName === "BidPlaced") {
        const { jobId, bidId, bidder, price } = parsed.args as {
          jobId: bigint;
          bidId: bigint;
          bidder: `0x${string}`;
          price: bigint;
        };
        decoded.push({
          id: `${log.transactionHash}-bid-${bidId}`,
          type: "BidPlaced",
          title: `Bid #${bidId.toString()} on job #${jobId.toString()}`,
          amount: Number(formatUnits(price, 18)),
          wallet: bidder,
          ...base,
        });
      } else if (parsed.eventName === "BidAccepted") {
        const { jobId, bidId, poster, agent } = parsed.args as {
          jobId: bigint;
          bidId: bigint;
          poster: `0x${string}`;
          agent: `0x${string}`;
        };
        decoded.push({
          id: `${log.transactionHash}-accept-${bidId}`,
          type: "BidAccepted",
          title: `Bid #${bidId.toString()} accepted for job #${jobId.toString()}`,
          amount: 0,
          wallet: poster || agent,
          ...base,
        });
      }
    } catch {
      // ignore unknown logs
      continue;
    }
  }

  return decoded;
}

