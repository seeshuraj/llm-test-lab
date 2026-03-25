import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function runModel(model: string, prompt: string) {
  const start = Date.now();
  const res = await openai.chat.completions.create({
    model,
    messages: [{ role: "user", content: prompt }],
    max_tokens: 512,
  });
  const latency = Date.now() - start;
  const output = res.choices[0].message.content ?? "";
  return { model, output, latency };
}

function scoreOutput(output: string, expected: string) {
  const a = output.toLowerCase();
  const b = expected.toLowerCase();
  const words = b.split(/\s+/);
  const hits = words.filter((w) => a.includes(w)).length;
  return Math.round((hits / words.length) * 100);
}

export async function POST(req: NextRequest) {
  const { prompt, expected } = await req.json();
  const models = ["gpt-4o-mini", "gpt-3.5-turbo"];

  const results = await Promise.all(models.map((m) => runModel(m, prompt)));

  const scored = results.map((r) => ({
    ...r,
    score: scoreOutput(r.output, expected),
  }));

  return NextResponse.json({ results: scored });
}
