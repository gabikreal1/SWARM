import { providers, Wallet } from 'ethers';

import { OrderBook__factory } from '../../typechain-types/factories/contracts/OrderBook.sol/OrderBook__factory';
import { Escrow__factory } from '../../typechain-types/factories/contracts/Escrow.sol/Escrow__factory';
import { JobRegistry__factory } from '../../typechain-types/factories/contracts/JobRegistry__factory';
import { AgentRegistry__factory } from '../../typechain-types/factories/contracts/AgentRegistry__factory';
import { ReputationToken__factory } from '../../typechain-types/factories/contracts/ReputationToken.sol/ReputationToken__factory';
import { MockUSDC__factory } from '../../typechain-types/factories/contracts/mocks/MockUSDC__factory';

import deployments from '../../deployments/arc-5042002.json';

type ConnOpts = {
  rpcUrl?: string;
  privateKey?: string;
  deploymentsPath?: string; // optional override (not used by default)
};

export async function getContracts(opts: ConnOpts = {}) {
  const rpcUrl = opts.rpcUrl || process.env.ARC_RPC_URL;
  if (!rpcUrl) throw new Error('RPC URL required: set opts.rpcUrl or ARC_RPC_URL');

  const provider = new providers.JsonRpcProvider(rpcUrl);

  const pk = opts.privateKey || process.env.ARC_PRIVATE_KEY;
  const signer = pk ? new Wallet(pk, provider) : undefined;

  // Use the deployments JSON shipped in the repo by default
  const deployed: any = deployments;

  const instances: any = { provider, signer, deployed };

  if (deployed?.contracts?.OrderBook) {
    instances.orderBook = OrderBook__factory.connect(deployed.contracts.OrderBook, signer ?? provider);
  }
  if (deployed?.contracts?.Escrow) {
    instances.escrow = Escrow__factory.connect(deployed.contracts.Escrow, signer ?? provider);
  }
  if (deployed?.contracts?.JobRegistry) {
    instances.jobRegistry = JobRegistry__factory.connect(deployed.contracts.JobRegistry, signer ?? provider);
  }
  if (deployed?.contracts?.AgentRegistry) {
    instances.agentRegistry = AgentRegistry__factory.connect(deployed.contracts.AgentRegistry, signer ?? provider);
  }
  if (deployed?.contracts?.ReputationToken) {
    instances.reputationToken = ReputationToken__factory.connect(deployed.contracts.ReputationToken, signer ?? provider);
  }
  if (deployed?.usdc) {
    instances.usdc = MockUSDC__factory.connect(deployed.usdc, signer ?? provider);
  }

  return instances;
}

export default getContracts;
