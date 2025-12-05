import { notFound } from "next/navigation";
import { WalletActions } from "@/components/wallet-actions";
import { prisma } from "@/lib/prisma";

type Params = {
  params: { id: string };
};

const demoRecipient = "0x000000000000000000000000000000000000dEaD";

export default async function AgentDetail({ params }: Params) {
  const id = Number(params.id);
  if (Number.isNaN(id)) return notFound();

  const agent = await prisma.agent.findUnique({
    where: { id },
    include: { owner: { select: { name: true, email: true, walletAddress: true } } },
  });

  if (!agent) return notFound();

  const recipient = agent.owner?.walletAddress || demoRecipient;

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-12">
      <div className="glass rounded-3xl p-8">
        <div className="flex items-center justify-between">
          <div className="pill">{agent.category || "General"}</div>
          <div className="text-sm text-[var(--muted)]">
            Network: {agent.network?.toUpperCase() || "EVM"}
          </div>
        </div>
        <h1 className="mt-3 text-3xl font-semibold text-[var(--foreground)]">
          {agent.title}
        </h1>
        <p className="mt-2 text-[var(--muted)]">{agent.description}</p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
          {agent.tags?.split(",").map((tag) => (
            <span key={tag} className="rounded-full bg-[var(--pill)] px-3 py-1">
              {tag.trim()}
            </span>
          ))}
        </div>
        <div className="mt-4 text-2xl font-semibold text-[var(--foreground)]">
          ${agent.priceUsd}
        </div>
        <div className="mt-1 text-sm text-[var(--muted)]">
          by {agent.owner?.name || agent.owner?.email}
        </div>
        {agent.owner?.walletAddress && (
          <div className="mt-1 text-xs text-[var(--muted)]">
            Payout wallet: {agent.owner.walletAddress}
          </div>
        )}
      </div>

      <WalletActions
        recipient={recipient}
        defaultAmount={0.01}
        agentId={agent.id}
      />
      <p className="text-xs text-[var(--muted)]">
        {agent.owner?.walletAddress
          ? "Funds route to the agent owner wallet set in their profile."
          : "No payout wallet set yet; using burn address as placeholder."}
      </p>
    </main>
  );
}

