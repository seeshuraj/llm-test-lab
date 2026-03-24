import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const FILE = path.join(process.cwd(), "waitlist.json");

export async function POST(req: NextRequest) {
  const { email } = await req.json();
  if (!email) return NextResponse.json({ error: "No email" }, { status: 400 });

  let emails: string[] = [];
  if (fs.existsSync(FILE)) {
    emails = JSON.parse(fs.readFileSync(FILE, "utf-8"));
  }
  if (!emails.includes(email)) {
    emails.push(email);
    fs.writeFileSync(FILE, JSON.stringify(emails, null, 2));
  }

  console.log("Waitlist signup:", email);
  return NextResponse.json({ ok: true });
}
