const BASE = import.meta.env.VITE_API_URL ?? "";   // empty in dev (uses the proxy)

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "X-Admin-Token": localStorage.getItem("adminToken") ?? "",
  };
  if (typeof init.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}/api${path}`, {
    ...init,
    headers: { ...headers, ...(init.headers as object) },
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}