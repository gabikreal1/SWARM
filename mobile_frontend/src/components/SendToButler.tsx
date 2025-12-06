"use client";

import React, { useState } from 'react';
import { useAccount, useSendTransaction, useSwitchChain, useWaitForTransactionReceipt } from 'wagmi';
import { parseEther } from 'viem';

const BUTLER_ADDRESS = '0x741ae17d47d479e878adfb3c78b02db583c63d58';
const NEOX_TESTNET_ID = 12227332;

export const SendToButler: React.FC = () => {
  const { isConnected, chainId } = useAccount();
  const { switchChainAsync, isPending: isSwitching } = useSwitchChain();
  const { data: hash, isPending: isSending, sendTransactionAsync, error } = useSendTransaction();
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash });

  const [amount, setAmount] = useState('0.01');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSend = async () => {
    setLocalError(null);

    if (!isConnected) {
      setLocalError('Connect your wallet first.');
      return;
    }

    let value: bigint;
    try {
      value = parseEther(amount.trim() || '0');
      if (value <= BigInt(0)) {
        setLocalError('Enter an amount greater than 0.');
        return;
      }
    } catch (err) {
      setLocalError('Enter a valid amount of GAS.');
      return;
    }

    try {
      if (chainId !== NEOX_TESTNET_ID && switchChainAsync) {
        await switchChainAsync({ chainId: NEOX_TESTNET_ID });
      }

      await sendTransactionAsync({
        to: BUTLER_ADDRESS,
        value,
        chainId: NEOX_TESTNET_ID,
      });
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : String(err));
    }
  };

  const status = localError || error?.message;

  return (
    <div className="send-card">
      <div className="send-heading">
        <span className="send-title">Send GAS to Butler</span>
        <span className="send-subtitle">NeoX Testnet · GAS</span>
      </div>

      <div className="send-target" title="Butler address">
        {BUTLER_ADDRESS}
      </div>

      <div className="send-input-row">
        <input
          type="text"
          inputMode="decimal"
          className="send-input"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.01"
        />
        <button
          type="button"
          className="btn-primary send-button"
          onClick={handleSend}
          disabled={isSending || isSwitching}
        >
          {isSending ? 'Sending…' : isSwitching ? 'Switching…' : 'Send'}
        </button>
      </div>

      <div className="send-status">
        {!isConnected && !status && 'Connect wallet to send.'}
        {status && <span className="send-status-error">{status}</span>}
        {isConfirming && 'Waiting for confirmation…'}
        {isSuccess && hash && (
          <a
            href={`https://xt4scan.ngd.network/tx/${hash}`}
            target="_blank"
            rel="noreferrer"
            className="send-link"
          >
            View on explorer
          </a>
        )}
      </div>
    </div>
  );
};
