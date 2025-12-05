# SpoonAI Integration Helper (contracts/integrations/spoon)

This folder contains helper code to connect SpoonAI (or any external service) to the project's smart contracts.

Files added:
- `connector.ts` — exports `getContracts(opts?)` which returns typed contract instances (OrderBook, Escrow, JobRegistry, AgentRegistry, ReputationToken, MockUSDC) connected to a provider and optional signer.
- `exportABIs.ts` — extracts ABIs from TypeChain factories and writes JSON to `abi/`.

Usage
1. Ensure dependencies are installed in `contracts/` (run `npm install` in `contracts/`).
2. Either provide `ARC_RPC_URL` in your environment, or pass `rpcUrl` to `getContracts`.
3. If write operations are needed, provide `ARC_PRIVATE_KEY` (or pass `privateKey` to `getContracts`) — use a restricted key for automation.

Quick example (Node/TS):

```ts
import getContracts from './integrations/spoon/connector';

async function main() {
  const c = await getContracts({ rpcUrl: process.env.ARC_RPC_URL });
  console.log('OrderBook address:', c.deployed.contracts.OrderBook);
  const title = await c.orderBook.name?.();
  console.log('OrderBook name (if implemented):', title);
}

main().catch(console.error);
```

Export ABIs
Run the exporter to produce standalone ABI JSON files:

```bash
cd contracts
npx ts-node --files integrations/spoon/exportABIs.ts
```

Security
- Never commit private keys. Prefer a signer service (KMS/HSM) for production.
- For SpoonAI integration, provide read-only RPC access unless SpoonAI must sign txs.
