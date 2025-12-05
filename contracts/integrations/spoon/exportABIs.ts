import fs from 'fs';
import path from 'path';

import { OrderBook__factory } from '../../typechain-types/factories/contracts/OrderBook.sol/OrderBook__factory';
import { Escrow__factory } from '../../typechain-types/factories/contracts/Escrow.sol/Escrow__factory';
import { JobRegistry__factory } from '../../typechain-types/factories/contracts/JobRegistry__factory';
import { AgentRegistry__factory } from '../../typechain-types/factories/contracts/AgentRegistry__factory';
import { ReputationToken__factory } from '../../typechain-types/factories/contracts/ReputationToken.sol/ReputationToken__factory';
import { MockUSDC__factory } from '../../typechain-types/factories/contracts/mocks/MockUSDC__factory';

const outDir = path.join(__dirname, 'abi');
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

function tryAbi(factory: any) {
  return factory.abi ?? factory._abi ?? (factory as any).ABI ?? null;
}

const map = {
  OrderBook: OrderBook__factory,
  Escrow: Escrow__factory,
  JobRegistry: JobRegistry__factory,
  AgentRegistry: AgentRegistry__factory,
  ReputationToken: ReputationToken__factory,
  MockUSDC: MockUSDC__factory,
};

for (const [name, factory] of Object.entries(map)) {
  const abi = tryAbi(factory as any);
  if (!abi) {
    console.warn(`ABI not found in factory for ${name}; skipping`);
    continue;
  }
  const outPath = path.join(outDir, `${name}.json`);
  fs.writeFileSync(outPath, JSON.stringify({ abi }, null, 2));
  console.log(`Wrote ${outPath}`);
}

console.log('ABI export complete.');
