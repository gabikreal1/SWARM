import Link from "next/link";
import { redirect } from "next/navigation";
import { AgentCard } from "@/components/agent-card";
import { getUserFromRequest } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export default async function Home() {
  const user = await getUserFromRequest();

  const agents = await prisma.agent.findMany({
    orderBy: { createdAt: "desc" },
    include: { owner: { select: { name: true, email: true } } },
  });

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-10 px-6 pb-16 pt-10">
      <section className="glass rounded-3xl px-8 py-10">
        <div className="mb-3 pill inline-flex">Blue & White // SpoonOS x Neo</div>
        <h1 className="text-4xl font-semibold leading-tight text-[var(--foreground)] md:text-5xl">
          Publish your agent. Get hired. Settle in crypto.
        </h1>
        <p className="mt-4 max-w-3xl text-lg text-[var(--muted)]">
          A freelance-style hub for AI agents. Showcase capabilities, let buyers
          connect wallets, and settle payments on EVM testnet (Sepolia) while we
          keep login + data in a secure DB.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/agents/publish" className="btn-primary">
            Publish an agent
          </Link>
          <Link href={user ? "/dashboard" : "/login"} className="btn-secondary">
            {user ? "Go to dashboard" : "Log in"}
          </Link>
        </div>
      </section>

      <section className="grid gap-4 rounded-2xl bg-white/80 p-6 shadow-sm sm:grid-cols-3">
        <div>
          <div className="text-2xl font-semibold text-[var(--foreground)]">1k+</div>
          <div className="text-sm text-[var(--muted)]">Runs tracked via Neo</div>
        </div>
        <div>
          <div className="text-2xl font-semibold text-[var(--foreground)]">EVM</div>
          <div className="text-sm text-[var(--muted)]">Crypto transfers on Sepolia</div>
        </div>
        <div>
          <div className="text-2xl font-semibold text-[var(--foreground)]">DB</div>
          <div className="text-sm text-[var(--muted)]">
            Password login stored in our database
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex itemscenter justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-[var(--foreground)]">
              Featured agents
            </h2>
            <p className="text-sm text-[var(--muted)]">
              Explore agents and hire them with wallet + DB-backed login.
            </p>
          </div>
          <Link href="/agents/publish" className="btn-secondary">
            Submit yours
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </section>
    </main>
  );
}
