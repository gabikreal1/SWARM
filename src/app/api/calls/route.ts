import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/calls
 * Returns recent call summaries.
 */
export async function GET() {
  const calls = await prisma.callSummary.findMany({
    orderBy: { createdAt: "desc" },
    take: 50,
  });
  return NextResponse.json({ calls });
}

type IncomingCallSummary = {
  conversationId?: string;
  callSid?: string;
  status?: string;
  summary?: string;
  toNumber?: string;
  jobId?: string;
  neofsUri?: string;
  payload?: unknown;
};

/**
 * POST /api/calls
 * Body: { conversationId?, callSid?, status?, summary?, toNumber?, jobId?, neofsUri?, payload? }
 * Header: x-call-summary-secret must match CALL_SUMMARY_SECRET (or ELEVENLABS_WEBHOOK_SECRET)
 */
export async function POST(req: NextRequest) {
  const secret =
    process.env.CALL_SUMMARY_SECRET || process.env.ELEVENLABS_WEBHOOK_SECRET;
  const provided =
    req.headers.get("x-call-summary-secret") ||
    req.headers.get("x-elevenlabs-signature") ||
    req.headers.get("x-webhook-secret");

  if (secret && provided !== secret) {
    return NextResponse.json({ error: "invalid secret" }, { status: 401 });
  }

  let body: IncomingCallSummary;
  try {
    body = (await req.json()) as IncomingCallSummary;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  // If fields are inside payload, prefer top-level but fall back to payload
  const payload = (body.payload as any) || {};
  const neofsUri = body.neofsUri || payload.neofs_uri;

  const record = await prisma.callSummary.create({
    data: {
      conversationId: body.conversationId ?? payload.conversation_id ?? payload.conversationId,
      callSid: body.callSid ?? payload.callSid ?? payload.call_sid,
      status: body.status ?? payload.status ?? payload.call_status,
      summary: body.summary ?? payload.summary ?? payload.analysis ?? payload.transcript,
      toNumber: body.toNumber ?? payload.to ?? payload.to_number,
      jobId: body.jobId ?? payload.jobId ?? payload.job_id,
      neofsUri: neofsUri,
      payload: payload,
    },
  });

  return NextResponse.json({ saved: true, id: record.id });
}
