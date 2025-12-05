/* eslint-disable @typescript-eslint/no-require-imports */
// Simple seed script to create a demo user and sample agents
require("dotenv").config();
const { PrismaClient } = require("@prisma/client");
const bcrypt = require("bcryptjs");

const prisma = new PrismaClient();

async function main() {
  const existing = await prisma.user.findUnique({
    where: { email: "demo@swarm.ai" },
  });

  const passwordHash = await bcrypt.hash("password123", 10);

  const user =
    existing ??
    (await prisma.user.create({
      data: {
        email: "demo@swarm.ai",
        name: "Demo User",
        passwordHash,
        walletAddress: "0x000000000000000000000000000000000000dEaD",
      },
    }));

  await prisma.agent.upsert({
    where: { id: 1 },
    update: {},
    create: {
      title: "Lead Gen Agent",
      description:
        "Automates outreach and captures qualified leads across email and LinkedIn.",
      category: "Sales",
      priceUsd: 49,
      tags: "leadgen,outreach,crm",
      network: "neox-testnet",
      ownerId: user.id,
    },
  });

  await prisma.agent.upsert({
    where: { id: 2 },
    update: {},
    create: {
      title: "Support Copilot",
      description:
        "Triage and respond to support tickets with human-in-the-loop approvals.",
      category: "Support",
      priceUsd: 29,
      tags: "support,helpdesk",
      network: "neox-testnet",
      ownerId: user.id,
    },
  });
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });

