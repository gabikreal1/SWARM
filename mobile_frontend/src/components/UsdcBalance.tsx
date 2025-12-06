"use client";

import { formatUnits } from 'viem';
import { useAccount, useReadContract } from 'wagmi';

const USDC_ADDRESS = '0x9f1Af8576f52507354eaF2Dc438a5333Baf2D09D';
const NEOX_TESTNET_ID = 12227332;

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

export function UsdcBalance() {
  const { address, status } = useAccount();

  const { data, isLoading, error, isFetching } = useReadContract({
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

  const notConnected = status !== 'connected' || !address;

  let content: string;
  if (notConnected) {
    content = 'Connect wallet to view mUSDC balance';
  } else if (error) {
    content = 'Unable to load balance';
  } else if (isLoading || isFetching) {
    content = 'Loading balance…';
  } else {
    const raw = data ?? BigInt(0);
    const formatted = formatUnits(raw, 6);
    content = `${formatted} mUSDC`;
  }

  return (
    <div className="flex items-center gap-2 rounded-xl bg-slate-900/70 border border-slate-700 px-3 py-2 text-xs text-gray-100">
      <span className="font-semibold">Balance</span>
      <span className="text-gray-300">{content}</span>
    </div>
  );
}
