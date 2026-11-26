export type User = { id: string; email: string; role: string; team_id: string | null; disabled: boolean };
export type Env = {
  id: string; name: string; template: string; size: string; desired_state: string;
  observed_state: string; isolation_tier: string; cpu_millis: number; mem_mb: number;
  storage_mb: number; expires_at: string;
};
export type Job = { id: string; kind: string; env_id: string; status: string; input: Record<string, unknown>; result: Record<string, unknown>; created_at: string };
export type Event = { id: number; ts: string; severity: string; kind: string; message: string; env_id: string | null };
export type Page<T> = { items: T[]; next_cursor: string | null };

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = typeof data === "object" && data !== null && "error" in data ? data.error : null;
    const message = typeof error === "object" && error !== null && "message" in error && typeof error.message === "string"
      ? error.message : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}

export const api = {
  health: () => request<{ status: string; db: boolean }>("/healthz"),
  login: (email: string, password: string) => request<{ user: User; csrf_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: (csrf: string) => request<void>("/auth/logout", { method: "POST", headers: { "X-CSRF-Token": csrf } }),
  me: () => request<{ user: User; csrf_token: string }>("/auth/me"),
  envs: () => request<Page<Env>>("/envs?limit=100"),
  templates: () => request<{ items: Array<{ name: string; title: string; sizes: string[] }> }>("/templates"),
  createEnv: (csrf: string, body: { name: string; template: string; size: string }) => request<Env>("/envs", { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) }),
  stopEnv: (csrf: string, id: string) => request<Env>(`/envs/${id}/stop`, { method: "POST", headers: { "X-CSRF-Token": csrf } }),
  deleteEnv: (csrf: string, id: string) => request<Env>(`/envs/${id}`, { method: "DELETE", headers: { "X-CSRF-Token": csrf } }),
  jobs: () => request<Page<Job>>("/jobs?limit=100"),
  exec: (csrf: string, envId: string, command: string) => request<Job>(`/envs/${envId}/exec`, { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify({ command, container: "toolbox" }) }),
  events: () => request<Page<Event>>("/events?limit=50"),
  overview: () => request<Record<string, unknown>>("/admin/overview"),
  activityStream: () => new EventSource(`${BASE}/stream`, { withCredentials: true }),
};
