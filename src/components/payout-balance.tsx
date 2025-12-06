"use client";

import { useBalance } from "wagmi";
import { chainDefaults } from "@/lib/contracts";

type Props = {
  address?: string | null;
  inline?: boolean;
  title?: string;
};

export function PayoutBalance({ address, inline = false, title }: Props) {
  const { data, isLoading, error } = useBalance({
    address,
    chainId: chainDefaults.chainId,
    query: { enabled: Boolean(address) },
    watch: true,
  });

  const wrapperClass = inline ? "" : "rounded-lg border border-[var(--border)] bg-white px-3 py-2";
  const heading = title ?? "Payout wallet balance";
  const balanceContent =
    isLoading ? "Loading…" : data ? `${data.formatted} ${data.symbol}` : "—";

  return (
    <div className={wrapperClass}>
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">
        {heading}
      </div>
      <div className="text-sm text-[var(--muted)] break-words">
        {address || "Set a payout wallet to view balance."}
      </div>
      {!address && (
        <div className="text-sm text-[var(--muted)]">No address set.</div>
      )}
      {error ? (
        <div className="text-sm text-red-600">Balance error: {error.message}</div>
      ) : (
        <div className="text-xl font-semibold text-[var(--foreground)]">
          {balanceContent}
        </div>
      )}
    </div>
  );
}

