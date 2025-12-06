import { createPublicClient, formatUnits, http, decodeEventLog } from "viem";
import { chainDefaults } from "@/lib/contracts";
import { orderBookAbi } from "@/lib/abi/orderBook";

const orderBookEventAbi = [
  {
    type: "event",
    name: "JobPosted",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "poster", type: "address", indexed: true },
    ],
  },
] as const;

type Bid = {
  id: bigint;
  bidder: string;
  price: number;
  deliveryTime: number;
  reputation: bigint;
  accepted: boolean;
  createdAt: number;
  metadataURI: string;
};

type JobWithBids = {
  jobId: bigint;
  status: number;
  poster: string;
  acceptedBidId: bigint;
  hasDispute: boolean;
  bids: Bid[];
};

const STATUS_LABEL: Record<number, string> = {
  0: "OPEN",
  1: "IN_PROGRESS",
  2: "DELIVERED",
  3: "COMPLETED",
  4: "DISPUTED",
};

async function fetchJobsWithBids(): Promise<JobWithBids[]> {
  if (!chainDefaults.orderBook) return [];

  const client = createPublicClient({
    transport: http(chainDefaults.rpcUrl),
    chain: {
      id: chainDefaults.chainId,
      name: chainDefaults.chainName,
      nativeCurrency: { name: "GAS", symbol: "GAS", decimals: 18 },
      rpcUrls: { default: { http: [chainDefaults.rpcUrl] } },
    },
  });

  // Discover job IDs from JobPosted events (last 50k blocks by default)
  const latestBlock = await client.getBlockNumber();
  const lookback = BigInt(process.env.NEXT_PUBLIC_ONCHAIN_LOOKBACK || 50000);
  const fromBlock = latestBlock > lookback ? latestBlock - lookback : 0n;

  const logs = await client.getLogs({
    address: chainDefaults.orderBook as `0x${string}`,
    fromBlock,
    toBlock: latestBlock,
  });

  const jobIds = new Set<bigint>();
  for (const log of logs) {
    try {
      const parsed = decodeEventLog({
        abi: orderBookEventAbi,
        data: log.data,
        topics: log.topics,
      });
      if (parsed.eventName === "JobPosted") {
        const { jobId } = parsed.args as { jobId: bigint };
        jobIds.add(jobId);
      }
    } catch {
      continue;
    }
  }

  const jobs: JobWithBids[] = [];
  for (const jobId of jobIds) {
    try {
      const res = await client.readContract({
        address: chainDefaults.orderBook as `0x${string}`,
        abi: orderBookAbi,
        functionName: "getJob",
        args: [jobId],
      });
      const job = res[0] as {
        poster: `0x${string}`;
        status: bigint;
        acceptedBidId: bigint;
        deliveryProof: string;
        hasDispute: boolean;
      };
      const bidsRaw = res[1] as any[];
      const bids: Bid[] = bidsRaw.map((b) => ({
        id: b.id,
        bidder: b.bidder,
        price: Number(formatUnits(b.price, 6)), // USDC 6 decimals
        deliveryTime: Number(b.deliveryTime),
        reputation: b.reputation,
        accepted: b.accepted,
        createdAt: Number(b.createdAt),
        metadataURI: b.metadataURI,
      }));
      jobs.push({
        jobId,
        status: Number(job.status),
        poster: job.poster,
        acceptedBidId: job.acceptedBidId,
        hasDispute: job.hasDispute,
        bids,
      });
    } catch {
      continue;
    }
  }

  return jobs.sort((a, b) => Number(b.jobId - a.jobId));
}

export default async function PublicJobsPage() {
  const jobs = await fetchJobsWithBids();

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-12">
      <div className="flex flex-col gap-2">
        <div className="pill w-fit">Public board</div>
        <h1 className="text-3xl font-semibold text-[var(--foreground)]">Jobs & bids</h1>
        <p className="text-[var(--muted)] max-w-3xl">
          Live view of on-chain jobs and all current bids. Hover rows to inspect details; accepted bids are highlighted.
        </p>
      </div>

      {jobs.length === 0 ? (
        <div className="card text-[var(--muted)]">No on-chain jobs found in the recent window.</div>
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => {
            const statusLabel = STATUS_LABEL[job.status] ?? `Status ${job.status}`;
            return (
              <div
                key={job.jobId.toString()}
                className="card border border-[var(--border)] bg-white/90 shadow-md transition hover:-translate-y-[1px] hover:shadow-lg"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="text-lg font-semibold text-[var(--foreground)]">Job #{job.jobId.toString()}</div>
                    <span className="pill">{statusLabel}</span>
                    {job.hasDispute && <span className="pill bg-red-100 text-red-700">Dispute</span>}
                    {job.acceptedBidId > 0 && (
                      <span className="pill bg-green-100 text-green-700">Accepted bid #{job.acceptedBidId.toString()}</span>
                    )}
                  </div>
                  <div className="text-xs text-[var(--muted)]">
                    Poster: {job.poster.slice(0, 6)}…{job.poster.slice(-4)}
                  </div>
                </div>

                <div className="mt-3 grid gap-2 rounded-xl border border-[var(--border)] bg-[#f8fbff] p-3">
                  {job.bids.length === 0 ? (
                    <div className="text-sm text-[var(--muted)]">No bids yet.</div>
                  ) : (
                    job.bids.map((bid) => (
                      <div
                        key={bid.id.toString()}
                        className={`flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white px-3 py-2 text-sm shadow-sm transition hover:-translate-y-[1px] hover:shadow-md ${
                          bid.accepted ? "ring-2 ring-[var(--accent)] ring-offset-1 ring-offset-white" : ""
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="pill bg-[var(--pill)] text-[var(--foreground)]">Bid #{bid.id.toString()}</span>
                          {bid.accepted && <span className="pill bg-green-100 text-green-700">Accepted</span>}
                        </div>
                        <div className="flex flex-wrap items-center gap-4 text-[var(--foreground)]">
                          <span className="font-semibold">{bid.price.toFixed(2)} USDC</span>
                          <span className="text-xs text-[var(--muted)]">
                            ETA: {Math.max(1, Math.round(bid.deliveryTime / 3600))}h
                          </span>
                          <span className="text-xs text-[var(--muted)]">
                            Bidder: {bid.bidder.slice(0, 6)}…{bid.bidder.slice(-4)}
                          </span>
                          {bid.metadataURI && (
                            <span className="text-xs text-[var(--muted)] truncate max-w-[220px]">
                              Notes: {bid.metadataURI}
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}

