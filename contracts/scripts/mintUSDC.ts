import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

/**
 * Mint MockUSDC to specified addresses
 * 
 * Usage:
 * npx hardhat run scripts/mintUSDC.ts --network neoxTestnet
 */

async function main() {
  console.log("🪙 MockUSDC Minting Script\n");

  // Load deployment file
  const network = await ethers.provider.getNetwork();
  const chainId = network.chainId.toString();
  const deploymentPath = path.join(__dirname, "../deployments", `neox-testnet-${chainId}.json`);
  
  if (!fs.existsSync(deploymentPath)) {
    console.error(`❌ Deployment file not found: ${deploymentPath}`);
    console.log("Please deploy contracts first using: npx hardhat run scripts/deploy.ts --network neoxTestnet");
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf-8"));
  const usdcAddress = deployment.usdc;

  console.log(`📍 Network: ${network.name} (Chain ID: ${chainId})`);
  console.log(`💵 MockUSDC: ${usdcAddress}\n`);

  // Load MockUSDC contract
  const MockUSDC = await ethers.getContractAt("MockUSDC", usdcAddress);

  // Get addresses from environment or use defaults
  const addresses = [
    { name: "Butler (User)", address: process.env.BUTLER_ADDRESS || process.env.NEOX_ADDRESS },
    { name: "Worker Agent", address: process.env.WORKER_ADDRESS },
    { name: "Manager Agent", address: process.env.MANAGER_ADDRESS },
    { name: "Scraper Agent", address: process.env.SCRAPER_ADDRESS },
    { name: "Caller Agent", address: process.env.CALLER_ADDRESS },
  ].filter(item => item.address); // Remove undefined entries

  if (addresses.length === 0) {
    console.error("❌ No addresses found in environment variables.");
    console.log("\nPlease set the following in your .env file:");
    console.log("  BUTLER_ADDRESS=0x...  (or NEOX_ADDRESS)");
    console.log("  WORKER_ADDRESS=0x...");
    console.log("  MANAGER_ADDRESS=0x...");
    console.log("  SCRAPER_ADDRESS=0x...");
    console.log("  CALLER_ADDRESS=0x...");
    process.exit(1);
  }

  // Default mint amount: 10,000 USDC per address (6 decimals)
  const amountPerAddress = ethers.parseUnits(
    process.env.MINT_AMOUNT || "10000",
    6
  );

  console.log(`💰 Minting ${ethers.formatUnits(amountPerAddress, 6)} USDC to each address...\n`);

  // Mint to each address
  for (const { name, address } of addresses) {
    try {
      console.log(`🔄 ${name}: ${address}`);
      
      // Check current balance
      const currentBalance = await MockUSDC.balanceOf(address);
      console.log(`   Current: ${ethers.formatUnits(currentBalance, 6)} USDC`);

      // Mint
      const tx = await MockUSDC.mint(address, amountPerAddress);
      console.log(`   TX: ${tx.hash}`);
      await tx.wait();

      // Check new balance
      const newBalance = await MockUSDC.balanceOf(address);
      console.log(`   New: ${ethers.formatUnits(newBalance, 6)} USDC ✅\n`);
    } catch (error: any) {
      console.error(`   ❌ Failed: ${error.message}\n`);
    }
  }

  console.log("✅ Minting complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
