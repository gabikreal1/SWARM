import { create } from 'zustand';

interface WalletState {
  address: string | null;
  network: string | null;
  connecting: boolean;
  setAddress: (address: string | null) => void;
  setNetwork: (network: string | null) => void;
  setConnecting: (connecting: boolean) => void;
}

export const useWalletStore = create<WalletState>((set) => ({
  address: null,
  network: null,
  connecting: false,
  setAddress: (address) => set({ address }),
  setNetwork: (network) => set({ network }),
  setConnecting: (connecting) => set({ connecting }),
}));
