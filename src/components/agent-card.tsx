import Link from "next/link";

export type Agent = {
  id: number;
  title: string;
  description: string;
  category?: string | null;
  priceUsd: number;
  tags?: string | null;
  network?: string | null;
  owner?: {
    name: string | null;
    email: string;
  } | null;
};

export function AgentCard({
  agent,
  showManageLink = false,
}: {
  agent: Agent;
  showManageLink?: boolean;
}) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="pill">{agent.category || "General"}</div>
        <span className="text-sm text-[var(--muted)]">
          {agent.network?.toUpperCase() || "EVM"}
        </span>
      </div>
      <h3 className="text-lg font-semibold text-[var(--foreground)]">
        {agent.title}
      </h3>
      <p className="text-sm text-[var(--muted)] line-clamp-3">
        {agent.description}
      </p>
      <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)]">
        {agent.tags?.split(",").map((tag) => (
          <span key={tag} className="rounded-full bg-[var(--pill)] px-3 py-1">
            {tag.trim()}
          </span>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between">
        <div>
          <div className="text-sm text-[var(--muted)]">From</div>
          <div className="text-xl font-semibold">${agent.priceUsd}</div>
        </div>
        <div className="flex gap-2">
          <Link href={`/agents/${agent.id}`} className="btn-primary">
            View & Hire
          </Link>
          {showManageLink && (
            <Link
              href={`/agents/${agent.id}/edit`}
              className="btn-secondary whitespace-nowrap"
            >
              Edit
            </Link>
          )}
        </div>
      </div>
      {agent.owner ? (
        <div className="text-xs text-[var(--muted)]">
          by {agent.owner.name || agent.owner.email}
        </div>
      ) : null}
    </div>
  );
}

