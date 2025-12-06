import { useAccount, useBalance } from "wagmi";

/**
 * Simple balance display for the connected wallet (NeoLine on Neo X testnet).
 * Shows native GAS balance using wagmi/viem.
 */
export function WalletBalance() {
  const { address, isConnected, chainId } = useAccount();

  const { data, isLoading, error } = useBalance({
    address,
    chainId,
    watch: true, // auto-update on new blocks
  });

  if (!isConnected) return <div>Connect your wallet to see balance.</div>;
  if (error) return <div>Balance error: {error.message}</div>;
  if (isLoading) return <div>Loading balance...</div>;

  return (
    <div>
      <div>Wallet: {address}</div>
      <div>
        Balance: {data ? `${data.formatted} ${data.symbol}` : "—"}
      </div>
    </div>
  );
}

