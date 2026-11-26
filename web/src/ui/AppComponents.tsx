import { useEffect, useState } from "react";
import type * as React from "react";
import { api, sandboxActionsEnabled, type Env, type Event, type Job } from "../api";
type Tab = "overview" | "environments" | "jobs" | "files" | "ai-redteam" | "activity" | "users" | "teams" | "audit";
export function Login({ apiAvailable, onLogin }: { apiAvailable: boolean; onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { await onLogin(email, password); } catch (e) { setError(e instanceof Error ? e.message : "Sign in failed"); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-card">
    <div className="brand-mark">A</div><p className="eyebrow">SECURITY OPERATIONS</p><h1>ABHEDYA</h1>
    <p className="muted">Sign in to the ABHEDYA security operations console.</p>
    <p className={apiAvailable ? "notice-banner" : "error-banner"} role="status">{apiAvailable ? "API and database connected." : "API or database unavailable. Sign-in is disabled until the real API is healthy."}</p>
    <form onSubmit={submit} className="form-stack"><label>Email<input name="email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      {error && <p className="error-banner">{error}</p>}<button className="primary" disabled={busy || !apiAvailable}>{busy ? "Signing inâ€¦" : "Sign in"}</button>
    </form><p className="tiny muted">Authentication is handled by the ABHEDYA API. No demo credentials are built in.</p>
  </section></main>;
}

export function Overview({ envs, jobs, events, overview, onNavigate, canViewJobs, onKillSwitch }: { envs: Env[]; jobs: Job[]; events: Event[]; overview: Record<string, unknown> | null; onNavigate: (tab: Tab) => void; canViewJobs: boolean; onKillSwitch?: () => void }) {
  const alertCount = events.filter(e => e.severity === "critical" || e.severity === "warn").length;
  const states = Object.entries((overview?.envs_by_state ?? {}) as Record<string, number>);
  const isolation = overview?.isolation && typeof overview.isolation === "object" ? overview.isolation as Record<string, unknown> : null;
  const runtime = sandboxActionsEnabled && typeof isolation?.runtime === "string" ? isolation.runtime : "Not enabled";
  const degraded = isolation?.degraded === true;
  return <><section className="metrics-grid"><Metric label="Environments" value={envs.length} sub={`${envs.filter(e => e.observed_state === "running").length} running`} tone="blue" icon="â–¦" />
    {canViewJobs && <Metric label="Active jobs" value={jobs.filter(j => ["queued", "running"].includes(j.status)).length} sub={`${jobs.filter(j => j.status === "queued").length} queued`} tone="violet" icon="âŒ˜" />}
    <Metric label="Alerts" value={alertCount} sub="In recent activity" tone={alertCount ? "amber" : "green"} icon="âš‘" />
    <Metric label="Users" value={typeof overview?.users === "number" ? overview.users : "â€”"} sub="From authenticated API" tone="blue" icon="â™§" />
    <Metric label="Teams" value={typeof overview?.teams === "number" ? overview.teams : "â€”"} sub="From authenticated API" tone="violet" icon="â™™" />
    <Metric label="Sandbox runtime" value={runtime} sub={!sandboxActionsEnabled ? "Local website demo Â· no sandbox" : degraded ? "Degraded mode enabled" : overview ? "Configured Â· host proof pending" : "Admin API data unavailable"} tone={degraded ? "amber" : "blue"} icon="â›¨" /></section>
    <div className="dashboard-grid"><section className="panel span-2"><PanelTitle title="Environments" action="View all" onAction={() => onNavigate("environments")} />
      {envs.length ? <EnvironmentTable envs={envs.slice(0, 5)} busy={false} compact actionsEnabled={false} /> : <Empty title="No environments yet" text="Environment data appears here when returned by the API." />}</section>
      <section className="panel"><PanelTitle title="Recent activity" action="View all" onAction={() => onNavigate("activity")} />{events.length ? <EventList events={events.slice(0, 6)} /> : <Empty title="No activity recorded" text="API activity will appear here when available." />}</section>
      {canViewJobs && <section className="panel span-2"><PanelTitle title="Recent jobs" action="View jobs" onAction={() => onNavigate("jobs")} />{jobs.length ? <JobTable jobs={jobs.slice(0, 5)} compact /> : <Empty title="No jobs yet" text="Execution jobs appear after they are submitted through the API." />}</section>}
      <section className="panel"><PanelTitle title="Host allocation" />{overview ? <div className="host-facts">{states.map(([state, count]) => <div key={state}><span>{state}</span><b>{count}</b></div>)}<small>Runtime configuration is reported by the API; runsc isolation is not host-verified.</small>{onKillSwitch && <button className="danger-action" onClick={onKillSwitch}>Stop all environments</button>}</div> : <Empty title="Admin data unavailable" text="Host allocation is shown to admins when the API permits it." />}</section>
    </div></>;
}

function Metric({ label, value, sub, tone, icon }: { label: string; value: string | number; sub: string; tone: string; icon: string }) { return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><p>{label}</p><strong>{value}</strong><small>{sub}</small></article>; }
function PanelTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) { return <div className="panel-title"><h2>{title}</h2>{action && <button className="text-button" onClick={onAction}>{action} â†’</button>}</div>; }
function Empty({ title, text }: { title: string; text: string }) { return <div className="empty"><span>â—‡</span><strong>{title}</strong><p>{text}</p></div>; }
function UsageCell({ env }: { env: Env }) {
  const [sample, setSample] = useState<import("../api").MetricSample | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    const refresh = () => api.metrics(env.id).then(page => {
      if (active) { setSample(page.items.at(-1) ?? null); setFailed(false); }
    }).catch(() => { if (active) setFailed(true); });
    if (env.observed_state === "running") void refresh();
    const timer = env.observed_state === "running" ? window.setInterval(() => void refresh(), 5000) : undefined;
    return () => { active = false; if (timer !== undefined) window.clearInterval(timer); };
  }, [env.id, env.observed_state]);
  if (failed) return <span title="The API could not read usage metrics">Metrics unavailable</span>;
  if (!sample) return <span>{env.cpu_millis}m CPU Â· {env.mem_mb} MB RAM limit<br />No live sample yet</span>;
  return <span title={`Sample ${sample.ts}`}>{sample.cpu_pct.toFixed(1)}% CPU Â· {sample.mem_mb.toFixed(0)}/{env.mem_mb} MB RAM<br />{sample.storage_mb.toFixed(0)}/{env.storage_mb} MB storage Â· {sample.pids}/{env.pids_limit} processes</span>;
}
export function EnvironmentTable({ envs, busy, compact = false, actionsEnabled, onStop, onDelete, onExec }: { envs: Env[]; busy: boolean; compact?: boolean; actionsEnabled: boolean; onStop?: (env: Env) => void; onDelete?: (env: Env) => void; onExec?: (env: Env) => void }) {
  const actionsAvailable = actionsEnabled && Boolean(onStop && onDelete && onExec);
  if (!envs.length) return <Empty title="No environments found" text="Environment state will appear here when returned by the API." />;
  return <div className="table-wrap"><table><thead><tr><th>Environment</th><th>Template</th><th>Status</th>{!compact && <><th>Size</th><th>Isolation tier</th></>}<th>Usage / limits</th>{!compact && <th>Actions</th>}</tr></thead><tbody>{envs.map(env => <tr key={env.id}><td><div className="env-name"><span className="env-glyph">â–¦</span><span>{actionsAvailable ? <button className="env-link" onClick={() => onExec?.(env)}>{env.name}</button> : <strong>{env.name}</strong>}<small>{env.id.slice(0, 8)}</small></span></div></td><td>{env.template}</td><td><Badge value={env.observed_state} /></td>{!compact && <><td>{env.size}</td><td>{env.isolation_tier || "pending"}</td></>}<td><UsageCell env={env} /></td>{!compact && <td><div className="row-actions"><button disabled={!actionsAvailable || busy || env.observed_state !== "running"} onClick={() => onExec?.(env)}>Exec</button><button disabled={!actionsAvailable || busy || env.desired_state !== "running"} onClick={() => onStop?.(env)}>Stop</button><button disabled={!actionsAvailable || busy} onClick={() => onDelete?.(env)}>Delete</button></div></td>}</tr>)}</tbody></table></div>;
}
export function JobTable({ jobs, compact = false }: { jobs: Job[]; compact?: boolean }) { if (!jobs.length) return <Empty title="No jobs found" text="Jobs and their actual API results will appear here." />; return <div className="table-wrap"><table><thead><tr><th>Job</th><th>Kind</th><th>Status</th><th>Environment</th><th>Created</th>{!compact && <th>Result</th>}</tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td><code>{j.id.slice(0, 8)}</code></td><td>{j.kind}</td><td><Badge value={j.status} /></td><td><code>{j.env_id.slice(0, 8)}</code></td><td>{date(j.created_at)}</td>{!compact && <td className="result-cell">{typeof j.result?.output === "string" ? <pre>{j.result.output}</pre> : j.status === "queued" || j.status === "running" ? "Waiting for runner" : JSON.stringify(j.result ?? {})}</td>}</tr>)}</tbody></table></div>; }
export function EventTable({ events }: { events: Event[] }) { if (!events.length) return <Empty title="No activity found" text="Events are loaded from the authenticated API." />; return <div className="panel"><EventList events={events} /></div>; }
function EventList({ events }: { events: Event[] }) { return <div className="event-list">{events.map(e => <article className="event-item" key={e.id}><span className={`event-mark ${e.severity}`}>â€¢</span><div><b>{e.kind.replaceAll(".", " Â· ")}</b><p>{e.message}</p><small>{date(e.ts)} {e.env_id ? `Â· ${e.env_id.slice(0, 8)}` : ""}</small></div></article>)}</div>; }
function Badge({ value }: { value: string }) { return <span className={`badge ${value.toLowerCase().replaceAll("_", "-")}`}>{value.replaceAll("_", " ")}</span>; }
function date(value: string) { const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString(); }
export function CreateDialog({ templates, busy, onClose, onSubmit }: { templates: Array<{ name: string; title: string; sizes: string[] }>; busy: boolean; onClose: () => void; onSubmit: (name: string, template: string, size: string) => void }) {
  const [name, setName] = useState(""); const [template, setTemplate] = useState("app-target"); const [size, setSize] = useState("S");
  const available = templates.filter(item => item.name === "app-target");
  const selected = available.find(item => item.name === template);
  return <Dialog title="Create environment" onClose={onClose}><form className="form-stack" onSubmit={e => { e.preventDefault(); onSubmit(name, template, size); }}>
    <p className="muted">Only app-target creation is currently accepted by the implemented API. Provisioning also requires a configured runner and locally available approved images.</p>
    <label>Name<input name="name" required minLength={3} maxLength={32} pattern="[a-z0-9-]{3,32}" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. incident-review" /></label>
    <label>Template<select value={template} onChange={e => setTemplate(e.target.value)}>{available.map(t => <option key={t.name} value={t.name}>{t.title} ({t.name})</option>)}</select></label>
    <label>Size<select value={size} onChange={e => setSize(e.target.value)}>{(selected?.sizes ?? ["S", "M", "L"]).map(s => <option key={s}>{s}</option>)}</select></label>
    <div className="dialog-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy || !available.length}>{busy ? "Submittingâ€¦" : "Submit"}</button></div>
  </form></Dialog>;
}
export function ExecDialog({ env, busy, onClose, onSubmit }: { env: Env; busy: boolean; onClose: () => void; onSubmit: (env: Env, command: string) => void }) {
  const [command, setCommand] = useState("");
  return <Dialog title={`Run command Â· ${env.name}`} onClose={onClose}><form className="form-stack" onSubmit={e => { e.preventDefault(); onSubmit(env, command); }}><p className="muted">Commands are sent to the toolbox through R17 and run only if the API reports the environment is running.</p><label>Command<input name="command" required maxLength={4096} value={command} onChange={e => setCommand(e.target.value)} placeholder="whoami" /></label><div className="dialog-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy}>{busy ? "Queueingâ€¦" : "Run"}</button></div></form></Dialog>;
}
function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) { return <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><section className="modal" role="dialog" aria-modal="true" aria-label={title}><div className="modal-head"><h2>{title}</h2><button className="icon-button" aria-label="Close" onClick={onClose}>Ã—</button></div>{children}</section></div>; }
