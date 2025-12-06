"use client";

import React from 'react';
import { useWalletStore } from './walletStore';

export const WalletConnectPanel: React.FC = () => {
  const { address, network, setAddress, setNetwork } = useWalletStore();

  const onConnectPress = () => {
    // TODO: integrate wagmi + NeoX-compatible wallet (NeoLine / O3, WalletConnect, etc.)
    setAddress('0xDEMO_NEOX_ADDRESS');
    setNetwork('NeoX Testnet');
  };

  return (
    <div className="card wallet-panel">
      <div className="card-header">Wallet</div>
      <div className="card-body">
        {address ? (
          <>
            <div className="wallet-address" title={address || undefined}>
              {address}
            </div>
            <div className="wallet-network">{network}</div>
          </>
        ) : (
          <>
            <p className="wallet-desc">
              Connect your NeoX wallet (NeoLine / O3) to manage escrow and jobs.
            </p>
            <button className="btn-primary" type="button" onClick={onConnectPress}>
              Connect Wallet
            </button>
          </>
        )}
      </div>
    </div>
  );
};
