"use client";

import React, { useEffect, useState } from 'react';
import { useAccount, useConnect, useDisconnect } from 'wagmi';

const truncateAddress = (address: string) => {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

export const WalletConnectButton: React.FC = () => {
  const [mounted, setMounted] = useState(false);
  const { address, isConnected, status: accountStatus } = useAccount();
  const { connectors, connect, status: connectStatus, error } = useConnect();
  const { disconnect } = useDisconnect();

  useEffect(() => {
    setMounted(true);
  }, []);

  const primaryConnector = connectors[0];
  const isConnecting = connectStatus === 'pending';

  if (isConnected && mounted) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-200 bg-slate-900/60 border border-slate-700 px-2 py-1 rounded-full">
          {truncateAddress(address || '')}
        </span>
        <button
          type="button"
          onClick={() => disconnect()}
          className="btn-secondary"
        >
          Disconnect
        </button>
      </div>
    );
  }

  const disabled = !mounted || connectors.length === 0 || isConnecting || accountStatus === 'connecting';
  const label = isConnecting ? 'Connecting…' : 'Connect Wallet';

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        className="btn-primary"
        onClick={() => primaryConnector && connect({ connector: primaryConnector })}
        disabled={disabled}
      >
        {label}
      </button>
      {!primaryConnector && mounted && (
        <span className="text-xs text-yellow-400">Install a wallet (e.g., MetaMask)</span>
      )}
      {error && (
        <span className="text-xs text-red-400" role="status">
          {error.message}
        </span>
      )}
    </div>
  );
};
