import Link from "next/link";
import { redirect } from "next/navigation";
import { AgentCard } from "@/components/agent-card";
import { TransactionList } from "@/components/transaction-list";
import { WalletPanel } from "@/components/wallet-panel";
import { EarningsPie } from "@/components/earnings-pie";
import { PayoutBalance } from "@/components/payout-balance";
import { fetchOrderBookEvents } from "@/lib/onchain-history";
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

  const earningsByAgent = orders.reduce<Record<number, number>>((acc, order) => {
    acc[order.agent.id] = (acc[order.agent.id] || 0) + order.amountEth;
    return acc;
  }, {});

  const mockEarnings: Record<string, number> = {
    "test agent": 100,
    "test 2 agent": 100,
    "test 2": 100,
    // Fallback for the displayed "Test" card to show the requested mock value.
    test: 300,
  };
  const defaultMockEarning = 300;

  const earningsData = agents.map((agent) => {
    const normalizedTitle = agent.title.trim().toLowerCase();
    const mock = mockEarnings[normalizedTitle] ?? defaultMockEarning;
    const base = earningsByAgent[agent.id] || 0;
    return {
      id: agent.id,
      title: agent.title,
      amount: base + mock,
    };
  });

  const onchainEvents = await fetchOrderBookEvents();
  const onchainOrders = onchainEvents.map((evt, idx) => ({
    id: `on-${idx}-${evt.id}`,
    txHash: evt.txHash || "unknown",
    amountEth: evt.amount,
    currency: evt.currency,
    network: evt.network,
    walletAddress: evt.wallet,
    createdAt: evt.createdAt,
    agent: { id: 0, title: evt.title },
    buyer: { email: evt.type },
    source: "on-chain" as const,
  }));

  const combinedOrders = [...orders.map((o) => ({
    ...o,
    source: "db" as const,
    createdAt: o.createdAt.toISOString(),
  })), ...onchainOrders].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );

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
          <PayoutBalance address={user.walletAddress} inline />
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
                  {earningsData
                    .find((entry) => entry.id === agent.id)
                    ?.amount.toFixed(2)}{" "}
                  GAS
                </div>
              </div>
            </div>
          ))
        )}
      </section>

      <EarningsPie
        data={earningsData.map((entry) => ({
          label: entry.title,
          value: entry.amount,
        }))}
      />

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
        <TransactionList orders={combinedOrders} />
      </section>
    </main>
  );
}

