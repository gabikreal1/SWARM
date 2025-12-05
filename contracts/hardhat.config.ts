import { config as dotenvConfig } from "dotenv";
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

dotenvConfig();

const accounts = process.env.NEOX_PRIVATE_KEY ? [process.env.NEOX_PRIVATE_KEY] : [];

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      chainId: 31337
    },
    // NeoX Testnet T4
    neoxTestnet: {
      url: process.env.NEOX_RPC_URL || "https://testnet.rpc.banelabs.org",
      chainId: 12227332,
      accounts,
      gasPrice: 40000000000, // 40 gwei
    },
    // NeoX Mainnet
    neoxMainnet: {
      url: "https://mainnet-1.rpc.banelabs.org",
      chainId: 47763,
      accounts,
      gasPrice: 40000000000, // 40 gwei
    },
    // Legacy Arc network (deprecated)
    arc: {
      url: process.env.ARC_RPC_URL || "",
      chainId: Number(process.env.ARC_CHAIN_ID || 5_042_002),
      accounts: process.env.ARC_PRIVATE_KEY ? [process.env.ARC_PRIVATE_KEY] : []
    }
  }
};

export default config;
