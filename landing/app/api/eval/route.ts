import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { supabase } from "@/lib/supabase";

const groq = new OpenAI({
  apiKey: process.env.GROQ_API_KEY,
  baseURL: "https://api.groq.com/openai/v1",
});

async function runGroq(model: string, prompt: string) {
  const start = Date.now();
  const res = await groq.chat.completions.create({
    model,
    messages: [{ role: "user", content: prompt }],
    max_tokens: 512,
  });
  const latency = Date.now() - start;
  return { model, output: res.choices[0].message.content ?? "", latency };
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

  const [llama70b, llama8b] = await Promise.all([
    runGroq("llama-3.3-70b-versatile", prompt),
    runGroq("llama-3.1-8b-instant", prompt),
  ]);

  const results = [llama70b, llama8b].map((r) => ({
    model: r.model,
    output: r.output,
    latency: r.latency,
    score: scoreOutput(r.output, expected),
  }));

  // Save each result to Supabase
  await supabase.from("eval_runs").insert(
    results.map((r) => ({
      prompt,
      expected,
      model: r.model,
      output: r.output,
      score: r.score,
      latency: r.latency,
    }))
  );

  return NextResponse.json({ results });
}
