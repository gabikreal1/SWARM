"use client";

import { useState } from "react";

type Props = {
  initialWallet?: string | null;
  name?: string | null;
};

export function WalletPanel({ initialWallet, name }: Props) {
  const [wallet, setWallet] = useState(initialWallet ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSave = async () => {
    setLoading(true);
    setStatus(null);
    const res = await fetch("/api/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ walletAddress: wallet }),
    });
    if (!res.ok) {
      const data = await res.json();
      setStatus(
        data?.error
          ? JSON.stringify(data.error)
          : "Could not save wallet address",
      );
      setLoading(false);
      return;
    }
    setStatus("Saved");
    setLoading(false);
  };

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="pill mb-2 w-fit">Payout wallet</div>
          <div className="text-lg font-semibold text-[var(--foreground)]">
            {name ? `${name}'s balance` : "Your balance"}
          </div>
          <div className="text-sm text-[var(--muted)]">
            Set your EVM address to receive payments for your agents.
          </div>
        </div>
      </div>
      <label className="text-sm text-[var(--muted)]">
        Wallet address (0x...)
        <input
          className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
          value={wallet}
          onChange={(e) => setWallet(e.target.value)}
          placeholder="0x..."
        />
      </label>
      <button className="btn-primary w-full" onClick={onSave} disabled={loading}>
        {loading ? "Saving..." : "Save wallet"}
      </button>
      {status && <div className="text-xs text-[var(--muted)]">{status}</div>}
    </div>
  );
}

