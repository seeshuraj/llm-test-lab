const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Safe storage — localStorage throws SecurityError in some iframe/sandbox
// contexts (Vercel preview, cross-origin iframes). Fall back to an in-memory
// store so the app doesn't crash.
// ---------------------------------------------------------------------------
const memoryStore: Record<string, string> = {};

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return memoryStore[key] ?? null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    memoryStore[key] = value;
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    delete memoryStore[key];
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function getToken(): string | null {
  return safeGet("token");
}

export function setToken(token: string): void {
  safeSet("token", token);
}

export function clearToken(): void {
  safeRemove("token");
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(email: string, password: string): Promise<string> {
  // FIX: was sending application/x-www-form-urlencoded with `username`.
  // Backend expects JSON with `email` field (UserLogin Pydantic model).
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid email or password");
  }
  const data = await res.json();
  return data.access_token;
}

export async function register(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  return data.access_token;
}

/**
 * Fetch current user profile — used to verify token validity on page load.
 * FIX: endpoint is /api/auth/me (with /api prefix).
 */
export async function fetchMe(): Promise<{ id: string; email: string; is_pro: boolean }> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("UNAUTHORIZED");
  return res.json();
}
