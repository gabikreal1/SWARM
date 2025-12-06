import { NextResponse } from "next/server";
import { fetchOrderBookEvents } from "@/lib/onchain-history";

export async function GET() {
  try {
    const events = await fetchOrderBookEvents();
    return NextResponse.json({ events });
  } catch (err) {
    console.error("onchain transactions error", err);
    return NextResponse.json(
      { error: "Failed to fetch on-chain transactions" },
      { status: 500 },
    );
  }
}

