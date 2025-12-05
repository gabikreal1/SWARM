/**
 * SpoonOS Environment Module
 * Exposes contract ABIs and instances as SpoonOS-compatible modules.
 * Import this in your SpoonOS agents and use the exported contract functions.
 */

import fs from 'fs';
import path from 'path';
import { providers, Wallet } from 'ethers';

import getContracts from './connector';
import deployments from '../../deployments/arc-5042002.json';

// Load ABI JSONs from the abi/ directory
const abiDir = path.join(__dirname, 'abi');

function loadABI(contractName: string) {
  try {
    const filePath = path.join(abiDir, `${contractName}.json`);
    if (!fs.existsSync(filePath)) {
      console.warn(`ABI file not found: ${filePath}`);
      return null;
    }
    const content = fs.readFileSync(filePath, 'utf8');
    const parsed = JSON.parse(content);
    return parsed.abi || parsed;
  } catch (e) {
    console.error(`Failed to load ABI for ${contractName}:`, e);
    return null;
  }
}

// Export ABIs as named exports for SpoonOS
export const ABIs = {
  OrderBook: loadABI('OrderBook'),
  Escrow: loadABI('Escrow'),
  JobRegistry: loadABI('JobRegistry'),
  AgentRegistry: loadABI('AgentRegistry'),
  ReputationToken: loadABI('ReputationToken'),
  MockUSDC: loadABI('MockUSDC'),
};

// Export deployed addresses
export const Deployments = deployments as any;

export const ContractAddresses = {
  orderBook: deployments?.contracts?.OrderBook,
  escrow: deployments?.contracts?.Escrow,
  jobRegistry: deployments?.contracts?.JobRegistry,
  agentRegistry: deployments?.contracts?.AgentRegistry,
  reputationToken: deployments?.contracts?.ReputationToken,
  usdc: deployments?.usdc,
  chainId: deployments?.chainId,
  network: deployments?.network,
};

// Factory function to get contract instances (used by SpoonOS agents)
export async function getContractInstances(opts?: { rpcUrl?: string; privateKey?: string }) {
  try {
    const instances = await getContracts(opts);
    return {
      orderBook: instances.orderBook,
      escrow: instances.escrow,
      jobRegistry: instances.jobRegistry,
      agentRegistry: instances.agentRegistry,
      reputationToken: instances.reputationToken,
      usdc: instances.usdc,
      provider: instances.provider,
      signer: instances.signer,
      addresses: ContractAddresses,
      abis: ABIs,
    };
  } catch (e) {
    console.error('Failed to get contract instances:', e);
    throw e;
  }
}

// Convenience export: info about the environment
export const EnvironmentInfo = {
  module: 'spoonos-env',
  version: '1.0.0',
  contracts: Object.keys(ContractAddresses),
  chainId: ContractAddresses.chainId,
  deployed: Deployments,
  requiredEnvVars: ['ARC_RPC_URL', 'ARC_PRIVATE_KEY'], // ARC_PRIVATE_KEY optional for read-only
};

export default {
  ABIs,
  Deployments,
  ContractAddresses,
  getContractInstances,
  EnvironmentInfo,
};
