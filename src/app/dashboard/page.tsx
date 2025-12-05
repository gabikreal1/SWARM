import Link from "next/link";
import { redirect } from "next/navigation";
import { AgentCard } from "@/components/agent-card";
import { TransactionList } from "@/components/transaction-list";
import { WalletPanel } from "@/components/wallet-panel";
import { OnchainPanel } from "@/components/onchain-panel";
import { getUserFromRequest } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const user = await getUserFromRequest();

  if (!user) {
    redirect("/login");
  }

  const agents = await prisma.agent.findMany({
    where: { ownerId: user.id },
    orderBy: { createdAt: "desc" },
    include: { owner: { select: { name: true, email: true } } },
  });

  const orders = await prisma.order.findMany({
    where: { agent: { ownerId: user.id } },
    orderBy: { createdAt: "desc" },
    include: { agent: { select: { id: true, title: true } }, buyer: { select: { email: true } } },
  });

  const totalEth = orders.reduce((acc, o) => acc + o.amountEth, 0);
  const earningsByAgent = orders.reduce<Record<number, number>>((acc, order) => {
    acc[order.agent.id] = (acc[order.agent.id] || 0) + order.amountEth;
    return acc;
  }, {});

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-12">
      <div className="flex flex-col gap-2">
        <div className="pill w-fit">Welcome back</div>
        <h1 className="text-3xl font-semibold text-[var(--foreground)]">
          {user.name || user.email}
        </h1>
        <p className="text-[var(--muted)]">
          Manage your published agents and payments.
        </p>
        <div className="flex gap-3">
          <Link href="/agents/publish" className="btn-primary">
            Publish new agent
          </Link>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[var(--muted)]">Total earned (on-chain)</div>
              <div className="text-3xl font-semibold text-[var(--foreground)]">
                {totalEth.toFixed(4)} ETH
              </div>
            </div>
            <div className="pill">Wallet balance</div>
          </div>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Earnings sum wallet-connected payments across your agents.
          </p>
        </div>
        <WalletPanel initialWallet={user.walletAddress} name={user.name || user.email} />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {agents.length === 0 ? (
          <div className="card">
            <p className="text-[var(--muted)]">
              No agents yet. Publish your first one.
            </p>
          </div>
        ) : (
          agents.map((agent) => (
            <div key={agent.id} className="flex flex-col gap-3">
              <AgentCard agent={agent} showManageLink />
              <div className="card flex items-center justify-between">
                <div className="text-sm text-[var(--muted)]">Earned</div>
                <div className="text-lg font-semibold text-[var(--foreground)]">
                  {(earningsByAgent[agent.id] || 0).toFixed(4)} ETH
                </div>
              </div>
            </div>
          ))
        )}
      </section>

      <OnchainPanel />

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Transaction history
            </h2>
            <p className="text-sm text-[var(--muted)]">
              Orders paid to your agents (wallet + DB).
            </p>
          </div>
        </div>
        <TransactionList
          orders={orders.map((o) => ({
            ...o,
            createdAt: o.createdAt.toISOString(),
          }))}
        />
      </section>
    </main>
  );
}

