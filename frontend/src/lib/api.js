import { get, set, del } from "idb-keyval";

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const QUEUE_KEY = "ruvia-outbox";
let tokens = null;
try { tokens = JSON.parse(localStorage.getItem("ruvia-auth") || "null"); } catch { tokens = null; }
const listeners = new Set();

export function onAuthChange(fn) { listeners.add(fn); return () => listeners.delete(fn); }
export function getTokens() { return tokens; }
export function setTokens(next) {
  tokens = next;
  try { next ? localStorage.setItem("ruvia-auth", JSON.stringify(next)) : localStorage.removeItem("ruvia-auth"); } catch { /* private mode */ }
  listeners.forEach((fn) => fn(next));
}

export class ApiError extends Error {
  constructor(message, status, data) { super(message); this.status = status; this.data = data; }
}

let refreshing = null;
async function refresh() {
  if (!tokens?.refresh) throw new ApiError("Signed out", 401);
  if (!refreshing) {
    refreshing = fetch(`${API_URL}/api/auth/refresh/`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: tokens.refresh }),
    }).then(async (r) => {
      if (!r.ok) { setTokens(null); throw new ApiError("Your session ended. Sign in again.", 401); }
      const data = await r.json();
      setTokens({ ...tokens, access: data.access, refresh: data.refresh || tokens.refresh });
    }).finally(() => { refreshing = null; });
  }
  return refreshing;
}

export async function api(path, { method = "GET", body, raw = false, auth = true, retry = true, form } = {}) {
  const headers = {};
  if (!form) headers["Content-Type"] = "application/json";
  if (auth && tokens?.access) headers.Authorization = `Bearer ${tokens.access}`;
  let res;
  try {
    res = await fetch(`${API_URL}/api${path}`, { method, headers, body: form || (body !== undefined ? JSON.stringify(body) : undefined) });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }
  if (res.status === 401 && auth && retry && tokens?.refresh) {
    await refresh();
    return api(path, { method, body, raw, auth, retry: false, form });
  }
  if (raw) {
    if (!res.ok) throw new ApiError("Request failed", res.status);
    return res;
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    const msg = data?.detail || Object.values(data || {}).flat().join(" ") || (res.status >= 500 ? "The server hit an error. Check the backend terminal." : "Something went wrong. Try again.");
    throw new ApiError(msg, res.status, data);
  }
  return data;
}

// Offline outbox: writes made without a connection are kept and replayed in order.
export async function queued(path, body, method = "POST") {
  try {
    return await api(path, { method, body });
  } catch (err) {
    if (err instanceof ApiError) throw err; // the server answered, so do not queue
    const outbox = (await get(QUEUE_KEY)) || [];
    outbox.push({ path, body, method, at: Date.now() });
    await set(QUEUE_KEY, outbox);
    return { queued: true };
  }
}

export async function outboxSize() { return ((await get(QUEUE_KEY)) || []).length; }

let flushing = false;
export async function flushOutbox() {
  if (flushing || !navigator.onLine || !tokens) return 0;
  flushing = true;
  let sent = 0;
  try {
    let outbox = (await get(QUEUE_KEY)) || [];
    while (outbox.length) {
      const item = outbox[0];
      try {
        await api(item.path, { method: item.method, body: item.body });
      } catch (err) {
        if (!(err instanceof ApiError)) break; // still offline
      }
      outbox = outbox.slice(1);
      await set(QUEUE_KEY, outbox);
      sent += 1;
    }
  } finally { flushing = false; }
  return sent;
}

export async function clearLocal() {
  await del(QUEUE_KEY);
  if ("caches" in window) {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("ruvia-api")).map((k) => caches.delete(k)));
  }
}

export async function downloadFile(path, filename) {
  const res = await api(path, { raw: true });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
