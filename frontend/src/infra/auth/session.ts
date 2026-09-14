import axios from "axios";

export const API_BASE_URL = (import.meta.env.VITE_API_ORIGIN ?? "http://localhost:8000")
  + (import.meta.env.VITE_API_PREFIX ?? "/api/v1");
let generation = 0;
let refreshPromise: Promise<string> | null = null;
const resetHandlers = new Set<() => void>();
const SESSION_CHANGE_KEY = "icinema:session-change";

export function sessionGeneration() { return generation; }
export function onSessionReset(handler: () => void) {
  resetHandlers.add(handler);
  return () => resetHandlers.delete(handler);
}

export function resetSessionData(broadcast = true) {
  generation += 1;
  refreshPromise = null;
  // Clear the old unscoped cache format as well as current user data.
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith("icinema:") && key.endsWith("-store")) localStorage.removeItem(key);
  }
  resetHandlers.forEach((handler) => handler());
  if (broadcast) localStorage.setItem(SESSION_CHANGE_KEY, `${Date.now()}:${Math.random()}`);
}

window.addEventListener("storage", (event: StorageEvent) => {
  if (event.storageArea !== localStorage || (event.key !== SESSION_CHANGE_KEY && event.key !== null)) return;
  resetSessionData(false);
  // Reinitialize identity and page-local forms as well as shared stores.
  window.location.reload();
});

export function expireAuthSession() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  resetSessionData();
  const redirect = window.location.pathname + window.location.search + window.location.hash;
  window.location.assign(`/auth/login?redirect=${encodeURIComponent(redirect)}`);
}

export function refreshAccessTokenOnce(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const token = localStorage.getItem("refresh_token");
  const startedGeneration = generation;
  if (!token) return Promise.reject(new Error("No refresh token"));
  const pending = axios.post<{ access_token: string; refresh_token: string }>(
    `${API_BASE_URL}/auth/refresh`, { refresh_token: token }, { timeout: 15000 },
  ).then(({ data }) => {
    if (startedGeneration !== generation || token !== localStorage.getItem("refresh_token")) {
      throw new Error("Session changed during refresh");
    }
    if (!data.access_token || !data.refresh_token) throw new Error("Incomplete token response");
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data.access_token;
  }).finally(() => {
    if (refreshPromise === pending) refreshPromise = null;
  });
  refreshPromise = pending;
  return pending;
}
