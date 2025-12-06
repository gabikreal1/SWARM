# Wallet Setup & USDC Minting Guide

## 1. Generate Wallets in MetaMask

Create **5 separate wallets** in MetaMask:
1. **Butler** (User wallet - posts jobs)
2. **Worker** (Simple bidder)
3. **Manager** (Orchestrator)
4. **Scraper** (TikTok/Web scraping)
5. **Caller** (Phone calls)

### Export Private Keys:
1. Open MetaMask
2. Click on account menu → Account details → Show private key
3. Copy each private key

## 2. Configure `.env` Files

### In `agents/.env`:
```env
NEOX_PRIVATE_KEY=0x...        # Butler wallet
WORKER_PRIVATE_KEY=0x...      # Worker wallet
MANAGER_PRIVATE_KEY=0x...     # Manager wallet
SCRAPER_PRIVATE_KEY=0x...     # Scraper wallet
CALLER_PRIVATE_KEY=0x...      # Caller wallet
```

### In `contracts/.env`:
```env
NEOX_PRIVATE_KEY=0x...        # Deployer wallet (can be Butler or separate)
BUTLER_ADDRESS=0x...          # Butler public address
WORKER_ADDRESS=0x...          # Worker public address
MANAGER_ADDRESS=0x...         # Manager public address
SCRAPER_ADDRESS=0x...         # Scraper public address
CALLER_ADDRESS=0x...          # Caller public address
```

## 3. Fund Wallets with GAS

**All 5 wallets need NeoX testnet GAS** for transaction fees:

1. Add NeoX Testnet to MetaMask:
   - **Network Name:** NeoX Testnet T4
   - **RPC URL:** `https://testnet.rpc.banelabs.org`
   - **Chain ID:** `12227332`
   - **Currency Symbol:** GAS
   - **Block Explorer:** `https://xt4scan.ngd.network`

2. Get testnet GAS from faucet **for each wallet**:
   - Visit: https://xt4faucet.ngd.network
   - Paste each wallet address (Butler, Worker, Manager, Scraper, Caller)
   - Request GAS
   - Wait for confirmation
   - **Repeat for all 5 wallets** - each needs its own GAS

### Why Each Agent Needs GAS:
- **Butler**: Posts jobs to OrderBook, accepts bids, approves deliveries
- **Worker/Manager/Scraper/Caller**: Register as agents, place bids, submit deliveries
- All transactions require gas fees to execute on NeoX blockchain

## 4. Mint MockUSDC

After deploying contracts, mint USDC to your wallets:

```bash
cd contracts
npx hardhat run scripts/mintUSDC.ts --network neoxTestnet
```

This will:
- Mint **10,000 USDC** to each wallet
- Show current and new balances
- Confirm each transaction

### Custom Mint Amount:
```bash
# Mint 50,000 USDC per wallet
MINT_AMOUNT=50000 npx hardhat run scripts/mintUSDC.ts --network neoxTestnet
```

## 5. Verify Setup

Check balances:
```bash
# In contracts folder
npx hardhat console --network neoxTestnet
```

Then in the console:
```javascript
const usdc = await ethers.getContractAt("MockUSDC", "0x..."); // Your USDC address
const balance = await usdc.balanceOf("0x..."); // Your wallet address
console.log(ethers.formatUnits(balance, 6), "USDC");
```

## Summary

| Wallet | Needs GAS | Needs USDC | Purpose | On-Chain Actions |
|--------|-----------|------------|---------|------------------|
| Butler | ✅ | ✅ | Posts jobs, pays agents | `postJob()`, `acceptBid()`, `approveDelivery()` |
| Worker | ✅ | ❌ | Places bids | `registerAgent()`, `placeBid()` |
| Manager | ✅ | ❌ | Orchestrates jobs | `registerAgent()`, `placeBid()`, `submitDelivery()` |
| Scraper | ✅ | ❌ | Executes scraping | `registerAgent()`, `placeBid()`, `submitDelivery()` |
| Caller | ✅ | ❌ | Makes phone calls | `registerAgent()`, `placeBid()`, `submitDelivery()` |

**Important:** All wallets need GAS for transaction fees. Request from faucet for each wallet address.
