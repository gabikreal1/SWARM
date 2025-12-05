import { NextResponse } from "next/server";
import { getUserFromRequest } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const user = await getUserFromRequest();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const orders = await prisma.order.findMany({
    where: { agent: { ownerId: user.id } },
    orderBy: { createdAt: "desc" },
    include: {
      agent: { select: { id: true, title: true } },
      buyer: { select: { email: true } },
    },
  });

  return NextResponse.json({ orders });
}

