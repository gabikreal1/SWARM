import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { agentSchema } from "@/lib/validators";
import { getUserFromRequest } from "@/lib/auth";

export async function GET() {
  const agents = await prisma.agent.findMany({
    orderBy: { createdAt: "desc" },
    include: { owner: { select: { id: true, email: true, name: true } } },
  });
  return NextResponse.json({ agents });
}

export async function POST(req: Request) {
  const user = await getUserFromRequest();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const parsed = agentSchema.safeParse({
    ...body,
    priceUsd: Number(body.priceUsd),
  });

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.flatten().fieldErrors },
      { status: 400 },
    );
  }

  const agent = await prisma.agent.create({
    data: {
      ...parsed.data,
      ownerId: user.id,
      tags: parsed.data.tags,
    },
  });

  return NextResponse.json({ agent });
}

