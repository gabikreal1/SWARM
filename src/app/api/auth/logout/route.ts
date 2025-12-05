import { NextResponse } from "next/server";
import { clearAuthCookieOnResponse } from "@/lib/auth";

export async function POST() {
  const res = NextResponse.json({ ok: true });
  clearAuthCookieOnResponse(res);
  return res;
}

