"use client";

import { useState } from "react";
import { parseEther } from "viem";
import {
  useAccount,
  useBalance,
  useConnect,
  useDisconnect,
  useSendTransaction,
} from "wagmi";

type Props = {
  recipient: string;
  defaultAmount?: number;
  agentId: number;
  network?: string;
};

export function WalletActions({
  recipient,
  defaultAmount = 0.01,
  agentId,
  network = "neox-testnet",
}: Props) {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending: isConnecting } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: balance } = useBalance({ address });
  const [amount, setAmount] = useState(defaultAmount.toString());
  const [status, setStatus] = useState<string | null>(null);

  const send = useSendTransaction({
    to: recipient as `0x${string}`,
    value: parseEther(amount || "0"),
  });

  const handleConnect = async () => {
    setStatus(null);
    const connector = connectors[0];
    if (!connector) {
      setStatus("No EVM wallet found. Install MetaMask or Rabby.");
      return;
    }
    await connect({ connector });
  };

  const handleSend = async () => {
    setStatus(null);
    try {
      const hash = await send.sendTransactionAsync();
      setStatus(`Tx sent: ${hash}`);
      await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId,
          txHash: hash,
          amountEth: Number(amount),
          network,
          walletAddress: address,
        }),
      });
    } catch (err) {
      console.error(err);
      setStatus("Transaction failed or rejected");
    }
  };

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-[var(--foreground)]">
          Crypto transfer (EVM)
        </div>
        {isConnected ? (
          <button className="text-sm text-[var(--muted)]" onClick={() => disconnect()}>
            Disconnect
          </button>
        ) : (
          <button
            className="btn-secondary"
            onClick={handleConnect}
            disabled={isConnecting}
          >
            {isConnecting ? "Connecting..." : "Connect Wallet"}
          </button>
        )}
      </div>

      {isConnected ? (
        <>
          <div className="text-sm text-[var(--muted)]">
            Connected: {address?.slice(0, 6)}...{address?.slice(-4)}
          </div>
          <div className="text-sm text-[var(--muted)]">
            Balance: {balance?.formatted} {balance?.symbol}
          </div>
          <label className="text-sm text-[var(--muted)]">
            Amount (ETH)
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-[var(--foreground)]"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              type="number"
              step="0.001"
              min="0"
            />
          </label>
          <button className="btn-primary w-full" onClick={handleSend}>
            Send to agent
          </button>
        </>
      ) : (
        <p className="text-sm text-[var(--muted)]">
          Connect your EVM wallet (MetaMask, Rabby, etc.) to fund this agent.
        </p>
      )}

      {status && <div className="text-xs text-[var(--muted)]">{status}</div>}
    </div>
  );
}

