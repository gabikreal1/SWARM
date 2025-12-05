import fs from 'fs';
import path from 'path';

const deploymentsPath = path.join(__dirname, '..', '..', 'deployments', 'arc-5042002.json');
const abiDir = path.join(__dirname, 'abi');

function exists(p: string) {
  try {
    return fs.existsSync(p);
  } catch (e) {
    return false;
  }
}

console.log('Checking deployments and ABI outputs');

if (!exists(deploymentsPath)) {
  console.error('Deployments JSON not found at', deploymentsPath);
  process.exit(2);
}

const dep = JSON.parse(fs.readFileSync(deploymentsPath, 'utf8'));

console.log('Deployment network info:');
console.log('  chainId:', dep.chainId ?? dep.network ?? '(unknown)');
console.log('  deployer:', dep.deployer ?? '(none)');

if (dep.contracts) {
  console.log('Contracts found:');
  for (const [name, addr] of Object.entries(dep.contracts)) {
    console.log(`  - ${name}: ${addr}`);
  }
} else {
  console.log('No contracts listed in deployments JSON');
}

console.log('\nChecking ABI files in', abiDir);
if (!exists(abiDir)) {
  console.warn('ABI directory not found — run exportABIs.ts to generate ABI JSONs');
  process.exit(0);
}

const expected = ['OrderBook', 'Escrow', 'JobRegistry', 'AgentRegistry', 'ReputationToken', 'MockUSDC'];
for (const name of expected) {
  const p = path.join(abiDir, `${name}.json`);
  if (!exists(p)) {
    console.warn(`  - ABI missing for ${name}: ${p}`);
  } else {
    const s = fs.statSync(p);
    console.log(`  - ABI ${name}: ${p} (${s.size} bytes)`);
  }
}

console.log('\nExample verification complete.');
