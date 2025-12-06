"use client";

import { useAccount, useBalance } from "wagmi";

/**
 * Shows the connected wallet's native GAS balance on Neo X.
 */
export function WalletBalance() {
  const { address, isConnected, chainId } = useAccount();
  const { data, isLoading, error } = useBalance({
    address,
    chainId,
    watch: true,
  });

  if (!isConnected) return <div>Connect your wallet to see balance.</div>;
  if (error) return <div>Balance error: {error.message}</div>;
  if (isLoading) return <div>Loading balance...</div>;

  return (
    <div>
      <div className="text-sm text-[var(--muted)]">Wallet: {address}</div>
      <div className="text-2xl font-semibold text-[var(--foreground)]">
        {data ? `${data.formatted} ${data.symbol}` : "—"}
      </div>
    </div>
  );
}

