import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

// Expected metadata shape
const metadataSchema = z.object({
  time: z.string(),
  date: z.string(),
  phone_to_call: z.string(),
  party_size: z.number(),
  user_name: z.string(),
  notes: z.string().optional().default(""),
  job_type: z.string().optional().default("call_verification"),
  tags: z.array(z.string()).optional().default([]),
});

const openaiModel = process.env.OPENAI_MODEL || "gpt-4.1";
const openaiKey = process.env.OPENAI_API_KEY || "";
const neofsGateway =
  process.env.NEOFS_REST_GATEWAY || "https://rest.fs.neo.org";
const neofsContainer = process.env.NEOFS_CONTAINER_ID || "";

async function callOpenAI(text: string) {
  if (!openaiKey) {
    throw new Error("OPENAI_API_KEY not set");
  }
  const prompt = `Extract structured call metadata from the text and return ONLY compact JSON matching:
{
  "time": "<string>",
  "date": "<string>",
  "phone_to_call": "<E.164 or raw>",
  "party_size": <number>,
  "user_name": "<string>",
  "notes": "<string>",
  "job_type": "call_verification",
  "tags": ["call","verification"]
}
Text: """${text}"""`;

  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${openaiKey}`,
    },
    body: JSON.stringify({
      model: openaiModel,
      messages: [
        { role: "system", content: "Return JSON only, no prose." },
        { role: "user", content: prompt },
      ],
      temperature: 0,
      response_format: { type: "json_object" },
    }),
  });
  if (!resp.ok) {
    const errTxt = await resp.text().catch(() => "");
    throw new Error(`OpenAI error: ${resp.status} ${errTxt}`);
  }
  const data = await resp.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) throw new Error("OpenAI response missing content");
  return JSON.parse(content);
}

async function uploadToNeoFS(json: any) {
  if (!neofsContainer) throw new Error("NEOFS_CONTAINER_ID not set");
  const payloadB64 = Buffer.from(JSON.stringify(json, null, 2)).toString(
    "base64"
  );
  const resp = await fetch(
    `${neofsGateway.replace(/\/$/, "")}/v1/objects/${neofsContainer}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        payload: payloadB64,
        attributes: {
          FileName: `job-metadata-${Date.now()}.json`,
          ContentType: "application/json",
          Type: "job_metadata",
        },
      }),
    }
  );
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`NeoFS upload failed: ${resp.status} ${txt}`);
  }
  const result = await resp.json();
  const objectId = result.object_id || result.oid;
  return `neofs://${neofsContainer}/${objectId}`;
}

export async function POST(req: NextRequest) {
  try {
    const { text } = (await req.json()) as { text?: string };
    if (!text || text.trim().length === 0) {
      return NextResponse.json({ error: "text is required" }, { status: 400 });
    }

    // LLM -> JSON
    const raw = await callOpenAI(text);
    const parsed = metadataSchema.parse(raw);

    // Upload to NeoFS
    const metadata = { ...parsed };
    const metadata_uri = await uploadToNeoFS(metadata);

    return NextResponse.json({ metadata, metadata_uri });
  } catch (err: any) {
    const msg = err?.message || "failed";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
