import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getUserFromRequest } from "@/lib/auth";

export async function POST(req: Request) {
  const user = await getUserFromRequest();
  const body = await req.json();

  const { agentId, txHash, amountEth, network, walletAddress } = body;

  if (!agentId || !txHash || !amountEth || !network || !walletAddress) {
    return NextResponse.json({ error: "Missing fields" }, { status: 400 });
  }

  const order = await prisma.order.create({
    data: {
      agentId: Number(agentId),
      txHash,
      amountEth: Number(amountEth),
      network,
      walletAddress,
      buyerId: user?.id,
    },
  });

  return NextResponse.json({ order });
}

