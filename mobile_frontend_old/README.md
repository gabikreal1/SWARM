# Swarm Butler Mobile PWA

React Native + Expo mobile-first PWA for the Swarm decentralized agent economy.

## Features (from PRD)

- 3D reactive sphere representing the agent swarm (Three.js via `expo-three`).
- Job feed showing OrderBook / agent activity.
- Wallet panel for NeoX wallet connection (NeoLine / O3) – currently stubbed.
- PWA-ready: runs in browser and installable on mobile.

## Getting Started

```bash
cd mobile_frontend
npm install
npm run web
```

Then open the printed localhost URL in your browser.

## Wallet Integration Notes

- `src/features/wallet/WalletConnectPanel.tsx` and `walletStore.ts` contain the connection state.
- Replace the placeholder `onConnectPress` logic with a real NeoX-compatible wallet bridge (e.g. WalletConnect or a NeoLine injected provider on web).
- For EVM-style RPC, you can integrate `viem` and point it at NeoX endpoints.

## 3D Sphere & Visualizer

- `src/components/ButlerSphere.tsx` sets up a metallic animated sphere using Three.js.
- Extend this component with custom shaders / audio-reactive behavior based on the PRD (Simplex noise, color shifts, etc.).

## Docs Index

Key design/architecture docs:

- Root `ACTIONABLE_PRD.md` – high-level Swarm product spec.
- `swarm-prd.md` (in your docs/downloads) – detailed flow and technology choices.
- `contracts/README.md` – smart contracts and on-chain layer.
- `agents/README.md` – backend agent mesh (Manager, Scraper, Caller, Butler).

This mobile PWA is the **Butler** interface on top of those layers.
