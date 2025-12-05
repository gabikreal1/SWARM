import { config as dotenvConfig } from "dotenv";
import type { Provider } from "ethers";
import { ethers } from "hardhat";
import path from "path";
import { promises as fs } from "fs";

dotenvConfig();

async function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 5,
  baseDelay = 2000
): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      const isTooManyRequests = 
        error?.message?.includes("Too Many Requests") ||
        error?.code === "ECONNRESET" ||
        error?.code === "ETIMEDOUT";
      
      if (!isTooManyRequests || i === maxRetries - 1) {
        throw error;
      }
      
      const delayMs = baseDelay * Math.pow(2, i);
      console.log(`Rate limited, retrying in ${delayMs}ms... (attempt ${i + 1}/${maxRetries})`);
      await delay(delayMs);
    }
  }
  throw new Error("Max retries exceeded");
}

async function main() {
  const [deployer] = await ethers.getSigners();
  const network = await deployer.provider.getNetwork();
  const chainId = Number(network.chainId);
  
  // Determine network name for file naming
  let networkName: string;
  if (chainId === 12227332) {
    networkName = "neox-testnet";
  } else if (chainId === 47763) {
    networkName = "neox-mainnet";
  } else if (chainId === 5042002) {
    networkName = "arc"; // legacy
  } else {
    networkName = `chain-${chainId}`;
  }

  console.log(`\n🚀 Deploying to ${networkName} (Chain ID: ${chainId})`);
  console.log(`   Deployer: ${deployer.address}`);
  const balance = await deployer.provider.getBalance(deployer.address);
  console.log(`   Balance: ${ethers.formatEther(balance)} GAS\n`);

  // Check if we should use MockUSDC or an existing USDC address
  let usdcAddress = process.env.USDC_TOKEN_ADDRESS;
  
  if (!usdcAddress) {
    console.log("📦 Deploying MockUSDC (no USDC_TOKEN_ADDRESS provided)...");
    const mockUSDC = await retryWithBackoff(() =>
      ethers.deployContract("MockUSDC")
    );
    await retryWithBackoff(() => mockUSDC.waitForDeployment());
    usdcAddress = mockUSDC.target as string;
    console.log(`   MockUSDC: ${usdcAddress}`);
    await delay(3000);
  } else {
    console.log(`📦 Using existing USDC: ${usdcAddress}`);
  }

  console.log("\n📦 Deploying JobRegistry...");
  const jobRegistry = await retryWithBackoff(() => 
    ethers.deployContract("JobRegistry", [deployer.address])
  );
  await retryWithBackoff(() => jobRegistry.waitForDeployment());
  console.log(`   JobRegistry: ${jobRegistry.target}`);
  await delay(3000);

  console.log("📦 Deploying ReputationToken...");
  const reputation = await retryWithBackoff(() =>
    ethers.deployContract("ReputationToken", [deployer.address])
  );
  await retryWithBackoff(() => reputation.waitForDeployment());
  console.log(`   ReputationToken: ${reputation.target}`);
  await delay(3000);

  console.log("📦 Deploying Escrow...");
  const escrow = await retryWithBackoff(() =>
    ethers.deployContract("Escrow", [deployer.address, usdcAddress, deployer.address])
  );
  await retryWithBackoff(() => escrow.waitForDeployment());
  console.log(`   Escrow: ${escrow.target}`);
  await delay(3000);

  console.log("📦 Deploying OrderBook...");
  const orderBook = await retryWithBackoff(() =>
    ethers.deployContract("OrderBook", [deployer.address, jobRegistry.target])
  );
  await retryWithBackoff(() => orderBook.waitForDeployment());
  console.log(`   OrderBook: ${orderBook.target}`);
  await delay(3000);

  console.log("📦 Deploying AgentRegistry...");
  const agentRegistry = await retryWithBackoff(() =>
    ethers.deployContract("AgentRegistry", [deployer.address])
  );
  await retryWithBackoff(() => agentRegistry.waitForDeployment());
  console.log(`   AgentRegistry: ${agentRegistry.target}`);

  const txOverrides = await buildTxOverrides(deployer.provider);

  // Send sequentially to avoid nonce collisions
  console.log("\n🔗 Wiring contracts together...");
  
  console.log("   Setting OrderBook in JobRegistry...");
  await retryWithBackoff(() => jobRegistry.setOrderBook(orderBook.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting OrderBook in Escrow...");
  await retryWithBackoff(() => escrow.setOrderBook(orderBook.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting Reputation in Escrow...");
  await retryWithBackoff(() => escrow.setReputation(reputation.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting Escrow in ReputationToken...");
  await retryWithBackoff(() => reputation.setEscrow(escrow.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting AgentRegistry in ReputationToken...");
  await retryWithBackoff(() => reputation.setAgentRegistry(agentRegistry.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting ReputationOracle in AgentRegistry...");
  await retryWithBackoff(() => agentRegistry.setReputationOracle(reputation.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting Escrow in OrderBook...");
  await retryWithBackoff(() => orderBook.setEscrow(escrow.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting ReputationToken in OrderBook...");
  await retryWithBackoff(() => orderBook.setReputationToken(reputation.target, txOverrides));
  await delay(3000);
  
  console.log("   Setting AgentRegistry in OrderBook...");
  await retryWithBackoff(() => orderBook.setAgentRegistry(agentRegistry.target, txOverrides));
  await delay(2000);

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const deploymentRecord = {
    network: networkName,
    chainId: chainId,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    usdc: usdcAddress,
    contracts: {
      JobRegistry: jobRegistry.target,
      ReputationToken: reputation.target,
      Escrow: escrow.target,
      OrderBook: orderBook.target,
      AgentRegistry: agentRegistry.target
    }
  } as const;

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  await fs.mkdir(deploymentsDir, { recursive: true });
  
  // Save timestamped version
  const timestampedPath = path.join(deploymentsDir, `${networkName}-${chainId}-${timestamp}.json`);
  await fs.writeFile(timestampedPath, JSON.stringify(deploymentRecord, null, 2));
  
  // Save latest version (overwrites)
  const latestPath = path.join(deploymentsDir, `${networkName}-${chainId}.json`);
  await fs.writeFile(latestPath, JSON.stringify(deploymentRecord, null, 2));

  console.log("\n✅ Deployment complete!");
  console.log("📄 Saved to:");
  console.log(`   Timestamped: ${timestampedPath}`);
  console.log(`   Latest: ${latestPath}`);
  
  console.log("\n📋 Contract Addresses:");
  console.log(`   USDC:            ${usdcAddress}`);
  console.log(`   JobRegistry:     ${jobRegistry.target}`);
  console.log(`   ReputationToken: ${reputation.target}`);
  console.log(`   Escrow:          ${escrow.target}`);
  console.log(`   OrderBook:       ${orderBook.target}`);
  console.log(`   AgentRegistry:   ${agentRegistry.target}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

async function buildTxOverrides(provider?: Provider | null) {
  // Support both env var names for compatibility
  const customGwei = process.env.NEOX_TX_GWEI || process.env.ARC_TX_GWEI;
  if (customGwei) {
    const fee = ethers.parseUnits(customGwei, "gwei");
    return {
      maxFeePerGas: fee,
      maxPriorityFeePerGas: fee / 2n
    } as const;
  }

  if (!provider) return undefined;

  const feeData = await provider.getFeeData();
  if (!feeData.maxFeePerGas || !feeData.maxPriorityFeePerGas) {
    return undefined;
  }

  const priority = (feeData.maxPriorityFeePerGas * 3n) / 2n; // +50%
  const maxFee = (feeData.maxFeePerGas * 3n) / 2n; // +50%

  return {
    maxFeePerGas: maxFee,
    maxPriorityFeePerGas: priority
  } as const;
}
