type Order = {
  id: number | string;
  txHash: string;
  amountEth: number;
  currency?: string;
  network: string;
  walletAddress: string;
  createdAt: string;
  agent: { id: number; title: string };
  buyer?: { email: string | null } | null;
  source?: "db" | "on-chain";
};

type Props = {
  orders: Order[];
};

export function TransactionList({ orders }: Props) {
  if (orders.length === 0) {
    return (
      <div className="card">
        <p className="text-[var(--muted)] text-sm">No transactions yet.</p>
      </div>
    );
  }

  return (
    <div className="card divide-y divide-[var(--border)] p-0">
      {orders.map((order) => (
        <div key={order.id} className="px-4 py-3 flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-[var(--foreground)]">
              {order.agent.title}
            </div>
            <div className="text-sm text-[var(--foreground)]">
              {order.amountEth} {order.currency || "GAS"}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)]">
            <span>{new Date(order.createdAt).toLocaleString()}</span>
            <span>Network: {order.network}</span>
            <span>Buyer: {order.buyer?.email || "wallet"}</span>
            {order.source && (
              <span className="pill bg-[var(--pill)] text-[var(--foreground)]">
                {order.source}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)] break-all">
            <span>From: {order.walletAddress}</span>
            <span>Tx: {order.txHash}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

