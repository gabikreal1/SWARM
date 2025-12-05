import { expect } from "chai";
import { ethers } from "hardhat";

describe("A2A marketplace flow", () => {
  it("runs full happy path", async () => {
    const [deployer, poster, agent] = await ethers.getSigners();

    const usdc = await ethers.deployContract("MockUSDC");
    await usdc.waitForDeployment();

    const agentRegistry = await ethers.deployContract("AgentRegistry", [deployer.address]);
    const jobRegistry = await ethers.deployContract("JobRegistry", [deployer.address]);
    const reputation = await ethers.deployContract("ReputationToken", [deployer.address]);
    const escrow = await ethers.deployContract("Escrow", [deployer.address, await usdc.getAddress(), deployer.address]);
    const orderBook = await ethers.deployContract("OrderBook", [deployer.address, await jobRegistry.getAddress()]);

    await Promise.all([
      jobRegistry.setOrderBook(orderBook.target),
      escrow.setOrderBook(orderBook.target),
      escrow.setReputation(reputation.target),
      reputation.setEscrow(escrow.target),
      reputation.setAgentRegistry(agentRegistry.target),
      agentRegistry.setReputationOracle(reputation.target),
      orderBook.setEscrow(escrow.target),
      orderBook.setReputationToken(reputation.target),
      orderBook.setAgentRegistry(agentRegistry.target)
    ]);

    const price = ethers.parseUnits("25", 6);
    await usdc.mint(poster.address, price);

    await agentRegistry.connect(agent).registerAgent("Research Agent", "ipfs://agent", ["research"]);

    const jobId = await orderBook
      .connect(poster)
      .postJob.staticCall("Find restaurants", "ipfs://job", ["restaurant"], 0);
    await orderBook.connect(poster).postJob("Find restaurants", "ipfs://job", ["restaurant"], 0);

    const bidId = await orderBook
      .connect(agent)
      .placeBid.staticCall(jobId, price, 3600, "ipfs://bid-metadata");
    await orderBook.connect(agent).placeBid(jobId, price, 3600, "ipfs://bid-metadata");

    await usdc.connect(poster).approve(escrow.target, price);
    await orderBook.connect(poster).acceptBid(jobId, bidId, "ipfs://response-answers");

    const escrowBalanceAfterLock = await usdc.balanceOf(escrow.target);
    expect(escrowBalanceAfterLock).to.equal(price);

    const proof = ethers.keccak256(ethers.toUtf8Bytes("delivery"));
    await orderBook.connect(agent).submitDelivery(jobId, proof);

    await orderBook.connect(poster).approveDelivery(jobId);

    const fee = price * BigInt(200) / BigInt(10_000);
    const expectedPayout = price - fee;
    const agentBalance = await usdc.balanceOf(agent.address);
    expect(agentBalance).to.equal(expectedPayout);

    const reputationScore = await reputation.scoreOf(agent.address);
    expect(reputationScore).to.be.greaterThan(0n);

    const jobData = await orderBook.getJob(jobId);
    expect(jobData[0].status).to.equal(3); // COMPLETED
  });
});
