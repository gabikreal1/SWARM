"use client";

import { useMemo, useState } from "react";
import { useAccount, useReadContract, useWriteContract } from "wagmi";
import { agentRegistryAbi } from "@/lib/abi/agentRegistry";
import { orderBookAbi } from "@/lib/abi/orderBook";
import { chainDefaults } from "@/lib/contracts";

const STATUS = ["Unregistered", "Active", "Inactive", "Banned"];

type AgentStruct = {
  name: string;
  metadataURI: string;
  capabilities: string[];
  reputation: bigint;
  status: bigint;
  createdAt: bigint;
  updatedAt: bigint;
};

export function OnchainPanel() {
  const { address, chainId } = useAccount();
  const [name, setName] = useState("");
  const [metadata, setMetadata] = useState("ipfs://your-agent-json");
  const [caps, setCaps] = useState("research,chat");
  const [jobDesc, setJobDesc] = useState("");
  const [jobMeta, setJobMeta] = useState("ipfs://job-details");
  const [jobTags, setJobTags] = useState("ai,agents");
  const [deadline, setDeadline] = useState("0");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const agentAddress = chainDefaults.agentRegistry as `0x${string}`;
  const orderBookAddress = chainDefaults.orderBook as `0x${string}`;

  const { data: agentData, refetch } = useReadContract({
    address: agentAddress,
    abi: agentRegistryAbi,
    functionName: "getAgent",
    args: address ? [address] : undefined,
    query: { enabled: Boolean(address) },
  });

  const { writeContractAsync, isPending } = useWriteContract();

  const agentStatus = useMemo(() => {
    if (!agentData) return "Unregistered";
    const typed = agentData as AgentStruct;
    const statusIndex = Number(typed.status ?? 0n);
    return STATUS[statusIndex] ?? "Unknown";
  }, [agentData]);

  const handleRegister = async () => {
    if (!address) {
      setStatusMsg("Connect wallet first");
      return;
    }
    if (chainId && chainId !== chainDefaults.chainId) {
      setStatusMsg(`Switch network to chain ${chainDefaults.chainId}`);
      return;
    }
    setStatusMsg("Submitting tx...");
    try {
      const capsList = caps.split(",").map((c) => c.trim()).filter(Boolean);
      const tx = await writeContractAsync({
        address: agentAddress,
        abi: agentRegistryAbi,
        functionName: "registerAgent",
        args: [name, metadata, capsList],
      });
      setStatusMsg(`Submitted: ${tx}`);
      await refetch();
    } catch (err) {
      setStatusMsg("Registration failed or rejected");
      console.error(err);
    }
  };

  const handlePostJob = async () => {
    if (!address) {
      setStatusMsg("Connect wallet first");
      return;
    }
    if (chainId && chainId !== chainDefaults.chainId) {
      setStatusMsg(`Switch network to chain ${chainDefaults.chainId}`);
      return;
    }
    setStatusMsg("Posting job...");
    try {
      const tags = jobTags.split(",").map((t) => t.trim()).filter(Boolean);
      const tx = await writeContractAsync({
        address: orderBookAddress,
        abi: orderBookAbi,
        functionName: "postJob",
        args: [jobDesc, jobMeta, tags, BigInt(deadline || "0")],
      });
      setStatusMsg(`Job posted tx: ${tx}`);
    } catch (err) {
      setStatusMsg("Job post failed or rejected");
      console.error(err);
    }
  };

  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="pill mb-2 w-fit">On-chain (Arc)</div>
          <div className="text-lg font-semibold text-[var(--foreground)]">
            Agent registry & jobs
          </div>
          <div className="text-sm text-[var(--muted)]">
            Chain {chainDefaults.chainId} · AgentRegistry {agentAddress.slice(0, 6)}… · OrderBook{" "}
            {orderBookAddress.slice(0, 6)}…
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <div className="text-sm font-semibold text-[var(--foreground)]">
            Register / update agent
          </div>
          <label className="text-sm text-[var(--muted)]">
            Name
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Onchain Agent"
            />
          </label>
          <label className="text-sm text-[var(--muted)]">
            Metadata URI (IPFS)
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={metadata}
              onChange={(e) => setMetadata(e.target.value)}
            />
          </label>
          <label className="text-sm text-[var(--muted)]">
            Capabilities (comma list)
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={caps}
              onChange={(e) => setCaps(e.target.value)}
            />
          </label>
          <button className="btn-primary" onClick={handleRegister} disabled={isPending}>
            {isPending ? "Sending..." : "Register on-chain"}
          </button>
          <div className="text-xs text-[var(--muted)]">
            Status: {agentStatus}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="text-sm font-semibold text-[var(--foreground)]">
            Post a job (OrderBook)
          </div>
          <label className="text-sm text-[var(--muted)]">
            Description
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={jobDesc}
              onChange={(e) => setJobDesc(e.target.value)}
              placeholder="Need an AI agent for…"
            />
          </label>
          <label className="text-sm text-[var(--muted)]">
            Metadata URI (IPFS)
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={jobMeta}
              onChange={(e) => setJobMeta(e.target.value)}
            />
          </label>
          <label className="text-sm text-[var(--muted)]">
            Tags
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={jobTags}
              onChange={(e) => setJobTags(e.target.value)}
            />
          </label>
          <label className="text-sm text-[var(--muted)]">
            Deadline (unix, 0 = none)
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              type="number"
              min="0"
            />
          </label>
          <button className="btn-secondary" onClick={handlePostJob} disabled={isPending}>
            {isPending ? "Sending..." : "Post job"}
          </button>
          <div className="text-xs text-[var(--muted)]">
            Jobs require the OrderBook to be wired to Escrow/USDC; this call only posts on-chain.
          </div>
        </div>
      </div>

      {statusMsg && <div className="text-xs text-[var(--muted)]">{statusMsg}</div>}
    </div>
  );
}

