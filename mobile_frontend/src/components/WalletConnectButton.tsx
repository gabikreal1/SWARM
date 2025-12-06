"use client";

import React, { useEffect, useState } from 'react';
import { useAccount, useConnect, useDisconnect, useReadContract } from 'wagmi';
import { formatUnits } from 'viem';

const USDC_ADDRESS = '0x9f1Af8576f52507354eaF2Dc438a5333Baf2D09D';
const NEOX_TESTNET_ID = 12227332;

const truncateAddress = (address: string) => {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

const isRequestResetError = (err: unknown) => {
  const message = (err as any)?.message || (err as any)?.toString?.() || '';
  return /connection request reset/i.test(message);
};

const erc20Abi = [
  {
    constant: true,
    inputs: [{ name: 'owner', type: 'address' }],
    name: 'balanceOf',
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
    type: 'function',
  },
] as const;

export const WalletConnectButton: React.FC = () => {
  const [mounted, setMounted] = useState(false);
  const { address, isConnected, status: accountStatus } = useAccount();
  const { connectors, connectAsync, status: connectStatus } = useConnect({
    mutation: {
      onError: (err) => {
        if (isRequestResetError(err)) {
          console.info('walletconnect pairing cancelled/reset');
          return;
        }
        console.error('wallet connect error', err);
      },
    },
  });
  const { disconnect } = useDisconnect();

  const { data: balanceData, isLoading: isBalLoading, isFetching: isBalFetching } = useReadContract({
    address: USDC_ADDRESS,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    chainId: NEOX_TESTNET_ID,
    query: {
      enabled: !!address,
      refetchInterval: 15000,
    },
  });

  useEffect(() => {
    setMounted(true);
    const suppressReset = (event: PromiseRejectionEvent) => {
      const message = (event.reason?.message || event.reason || '').toString();
      if (/connection request reset/i.test(message)) {
        event.preventDefault();
        console.info('walletconnect pairing cancelled/reset');
      }
    };
    window.addEventListener('unhandledrejection', suppressReset);
    return () => {
      window.removeEventListener('unhandledrejection', suppressReset);
    };
  }, []);

  const isConnecting = connectStatus === 'pending';

  const injectedAvailable = mounted
    ? connectors.find((c) => c.type === 'injected' && typeof window !== 'undefined' && !!(window as any).ethereum)
    : undefined;
  const walletConnectConnector = connectors.find((c) => c.id === 'walletConnect');
  const fallbackConnector = connectors.find((c) => c.id === 'metaMask' || c.id === 'coinbaseWallet' || c.type !== 'injected');
  const primaryConnector = injectedAvailable || walletConnectConnector || fallbackConnector || connectors[0];

  const disabled = !mounted || !primaryConnector || isConnecting || accountStatus === 'connecting';
  const label = isConnecting ? 'Connecting…' : 'Connect Wallet';

  const handleConnect = async () => {
    if (!primaryConnector) return;
    try {
      await connectAsync({ connector: primaryConnector });
    } catch (err) {
      if (isRequestResetError(err)) {
        console.info('walletconnect pairing cancelled/reset');
        return;
      }
      console.info('connect cancelled or failed', err);
      // swallow errors to keep UI clean
    }
  };

  const balanceView = (() => {
    if (!address) return { display: null, usd: null, loading: false };
    if (isBalLoading || isBalFetching) return { display: '…', usd: null, loading: true };
    if (balanceData === undefined) return { display: null, usd: null, loading: false };
    try {
      const formatted = formatUnits(balanceData ?? BigInt(0), 6);
      const num = Number.parseFloat(formatted);
      const main = Number.isFinite(num) ? num.toFixed(2) : formatted;
      return { display: `${main} mUSDC`, usd: null, loading: false };
    } catch (err) {
      console.info('balance format error', err);
      return { display: null, usd: null, loading: false };
    }
  })();

  if (isConnected && mounted) {
    return (
      <div className="wallet-chip">
        <div className="token-pill">
          <div className="token-icon">$
          </div>
          <div className="token-text">
            <span className="token-label">Balance</span>
            <span className="token-amount">{balanceView.display ?? '—'}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => disconnect()}
          className="btn-secondary wallet-disconnect"
          aria-label="Disconnect wallet"
        >
          <svg
            className="icon-exit"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fill="currentColor"
              d="M5 4a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v4h-2V4H7v16h6v-4h2v4a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4Zm13.707 7.293a1 1 0 0 1 0 1.414l-3 3a1 1 0 0 1-1.414-1.414L15.586 13H10v-2h5.586l-1.293-1.293a1 1 0 1 1 1.414-1.414l3 3Z"
            />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="wallet-chip">
      <button
        type="button"
        className="btn-primary wallet-connect"
        onClick={handleConnect}
        disabled={disabled}
      >
        {label}
      </button>
    </div>
  );
};
