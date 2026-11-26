export type User = { id: string; email: string; role: string; team_id: string | null; disabled: boolean };
export type Env = {
  id: string; name: string; template: string; size: string; desired_state: string;
  observed_state: string; isolation_tier: string; cpu_millis: number; mem_mb: number;
  storage_mb: number; pids_limit: number; expires_at: string;
};
export type MetricSample = { ts: string; cpu_pct: number; mem_mb: number; storage_mb: number; pids: number; net_rx_bytes: number; net_tx_bytes: number };
export type Job = { id: string; kind: string; env_id: string; status: string; input: Record<string, unknown>; result: Record<string, unknown>; created_at: string };
export type Event = { id: number; ts: string; severity: string; kind: string; message: string; env_id: string | null };
export type Team = { id: string; name: string; quota_envs: number; quota_cpu_millis: number; quota_mem_mb: number; quota_storage_mb: number; usage: { envs: number; cpu_millis: number; mem_mb: number; storage_mb: number } };
export type AuditRecord = { seq: number; ts: string; actor_id: string; actor_role: string; action: string; target_type: string; target_id: string; outcome: string; detail: Record<string, unknown>; hash: string };
export type Checkpoint = { tree_size: number; root_hash: string; head_hash: string; ts: string; signature: string; log_id: string };
export type VerifyResult = { ok: boolean; verdict: string; at: number | null; records: number; checkpoints: number; unanchored_tail: number; checked_at: string };
export type Page<T> = { items: T[]; next_cursor: string | null };

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
export const sandboxActionsEnabled = import.meta.env.VITE_SANDBOX_ACTIONS_ENABLED === "true";

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
  metrics: (envId: string) => request<{ items: MetricSample[] }>(`/envs/${envId}/metrics?minutes=1`),
  events: () => request<Page<Event>>("/events?limit=50"),
  overview: () => request<Record<string, unknown>>("/admin/overview"),
  users: () => request<Page<User>>("/users?limit=200"),
  teams: () => request<Page<Team>>("/teams?limit=200"),
  createUser: (csrf: string, body: { email: string; password: string; role: string; team_id: string | null }) => request<User>("/users", { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) }),
  updateUser: (csrf: string, id: string, body: { disabled?: boolean }) => request<User>(`/users/${id}`, { method: "PATCH", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) }),
  createTeam: (csrf: string, body: { name: string }) => request<Team>("/teams", { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) }),
  updateTeam: (csrf: string, id: string, body: { quota_envs: number; quota_cpu_millis: number; quota_mem_mb: number; quota_storage_mb: number }) => request<Team>(`/teams/${id}`, { method: "PATCH", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) }),
  killSwitch: (csrf: string) => request<{ affected: number }>("/admin/kill-switch", { method: "POST", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify({ team_id: null }) }),
  audit: (filters: { action?: string; outcome?: string }) => {
    const query = new URLSearchParams({ limit: "100" });
    if (filters.action) query.set("action", filters.action);
    if (filters.outcome) query.set("outcome", filters.outcome);
    return request<Page<AuditRecord>>(`/audit?${query.toString()}`);
  },
  checkpoints: () => request<{ items: Checkpoint[] }>("/audit/checkpoints"),
  verifyAudit: (csrf: string) => request<VerifyResult>("/audit/verify", { method: "POST", headers: { "X-CSRF-Token": csrf } }),
  exportAudit: async (kind: "records" | "checkpoints") => {
    const response = await fetch(`${BASE}/audit/export?kind=${kind}`, { credentials: "include", headers: { Accept: "application/x-ndjson" } });
    if (!response.ok) throw new ApiError(`Audit export failed (${response.status})`, response.status);
    return response.blob();
  },
  activityStream: () => new EventSource(`${BASE}/stream`, { withCredentials: true }),
};
