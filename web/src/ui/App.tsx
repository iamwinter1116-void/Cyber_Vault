import { useCallback, useEffect, useState } from "react";
import { api, type Env, type Event, type Job, type User } from "../api";

type Tab = "overview" | "environments" | "jobs" | "activity";

function Login({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
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
    <p className="muted">Sign in to the isolated testing console.</p>
    <form onSubmit={submit} className="form-stack"><label>Email<input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      {error && <p className="error-banner">{error}</p>}<button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    </form><p className="tiny muted">Authentication is handled by the ABHEDYA API. No demo credentials are built in.</p>
  </section></main>;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [csrf, setCsrf] = useState("");
  const [sessionChecked, setSessionChecked] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");
  const [envs, setEnvs] = useState<Env[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [streamLive, setStreamLive] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [templates, setTemplates] = useState<Array<{ name: string; title: string; sizes: string[] }>>([]);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [execEnv, setExecEnv] = useState<Env | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    setError("");
    try {
      const [envPage, jobPage, eventPage] = await Promise.all([api.envs(), api.jobs(), api.events()]);
      setEnvs(envPage.items); setJobs(jobPage.items); setEvents(eventPage.items);
      if (user.role === "admin") setOverview(await api.overview());
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load console data"); }
  }, [user]);

  useEffect(() => {
    api.health().then(h => setHealth(h.db ? "ok" : "down")).catch(() => setHealth("down"));
  }, []);
  useEffect(() => {
    let active = true;
    api.me().then(session => {
      if (active) { setUser(session.user); setCsrf(session.csrf_token); }
    }).catch(() => undefined).finally(() => {
      if (active) setSessionChecked(true);
    });
    return () => { active = false; };
  }, []);
  useEffect(() => { if (user) { void load(); api.templates().then(t => setTemplates(t.items)).catch(e => setError(e.message)); } }, [user, load]);
  useEffect(() => { if (!user) return; const timer = window.setInterval(() => void load(), 10000); return () => window.clearInterval(timer); }, [user, load]);
  useEffect(() => {
    if (!user) { setStreamLive(false); return; }
    const stream = api.activityStream();
    const onOpen = () => setStreamLive(true);
    const onError = () => setStreamLive(false);
    const onActivity = (raw: globalThis.Event) => {
      const message = raw as MessageEvent<string>;
      let event: unknown;
      try { event = JSON.parse(message.data) as unknown; } catch { return; }
      if (!isActivityEvent(event)) return;
      setEvents(previous => [event, ...previous.filter(item => item.id !== event.id)].slice(0, 200));
    };
    stream.addEventListener("open", onOpen);
    stream.addEventListener("error", onError);
    stream.addEventListener("activity", onActivity);
    return () => { stream.close(); setStreamLive(false); };
  }, [user]);

  async function signIn(email: string, password: string) {
    const session = await api.login(email, password);
    const established = await api.me();
    if (session.user.id !== established.user.id) throw new Error("The API session does not match the signed-in account");
    setUser(established.user); setCsrf(established.csrf_token);
  }
  async function signOut() { try { await api.logout(csrf); } finally { setUser(null); setCsrf(""); } }
  async function createEnvironment(name: string, template: string, size: string) {
    setBusy(true); setError("");
    try { await api.createEnv(csrf, { name, template, size }); setCreateOpen(false); setNotice("Environment request submitted."); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create environment"); }
    finally { setBusy(false); }
  }
  async function stopEnvironment(env: Env) {
    setBusy(true); setError("");
    try { await api.stopEnv(csrf, env.id); setNotice(`Stop requested for ${env.name}.`); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not stop environment"); }
    finally { setBusy(false); }
  }
  async function removeEnvironment(env: Env) {
    if (!window.confirm(`Request deletion of “${env.name}”?`)) return;
    setBusy(true); setError("");
    try { await api.deleteEnv(csrf, env.id); setNotice(`Deletion requested for ${env.name}.`); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not delete environment"); }
    finally { setBusy(false); }
  }
  async function runCommand(env: Env, command: string) {
    setBusy(true); setError("");
    try { await api.exec(csrf, env.id, command); setExecEnv(null); setNotice("Command queued. Results will appear in Jobs when the runner processes it."); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not queue command"); }
    finally { setBusy(false); }
  }

  if (!sessionChecked) return <main className="login-page"><section className="login-card"><div className="brand-mark">A</div><p className="eyebrow">SECURITY OPERATIONS</p><h1>ABHEDYA</h1><p className="muted">Checking your API session…</p></section></main>;
  if (!user) return <Login onLogin={signIn} />;
  const nav: Array<{ id: Tab; label: string; glyph: string }> = [
    { id: "overview", label: "Overview", glyph: "⌂" }, { id: "environments", label: "Environments", glyph: "▦" },
    { id: "jobs", label: "Jobs", glyph: "⌘" }, { id: "activity", label: "Activity", glyph: "◷" },
  ];
  return <div className="app-shell"><aside className="sidebar"><a className="brand" href="#overview" onClick={() => setTab("overview")}><span className="brand-mark small">A</span><span>ABHEDYA<small>SECURITY PLATFORM</small></span></a>
    <p className="nav-label">WORKSPACE</p><nav>{nav.map(item => <button key={item.id} className={tab === item.id ? "nav-item selected" : "nav-item"} onClick={() => setTab(item.id)}><span>{item.glyph}</span>{item.label}{item.id === "jobs" && jobs.some(j => j.status === "queued") && <i className="nav-dot" />}</button>)}</nav>
    <div className="sidebar-bottom"><div className="host-status"><span className={`status-dot ${health}`} />API {health === "ok" ? "connected" : health === "down" ? "unavailable" : "checking"}</div><div className="user-mini"><div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div><div className="user-label">{user.email}<small>{user.role.replace("_", " ")}</small></div><button className="icon-button" title="Sign out" onClick={() => void signOut()}>↗</button></div></div>
  </aside><main className="main-area"><header className="topbar"><div><span className="breadcrumb">Console</span><span className="slash">/</span><strong>{nav.find(n => n.id === tab)?.label}</strong></div><div className="top-actions"><span className="local-tag"><span className={`status-dot ${streamLive ? "ok" : "down"}`} />ACTIVITY {streamLive ? "STREAM LIVE" : "RECONNECTING"}</span><button className="icon-button refresh" title="Refresh data" onClick={() => void load()}>↻</button></div></header>
    <div className="content"><div className="page-heading"><div><p className="eyebrow">OPERATIONS / {tab.toUpperCase()}</p><h1>{tab === "overview" ? "Security overview" : nav.find(n => n.id === tab)?.label}</h1><p className="muted">{tab === "overview" ? "Live view of your isolated testing workspace." : "Data loaded from the authenticated ABHEDYA API."}</p></div>{tab === "environments" && <button className="primary" onClick={() => setCreateOpen(true)}>＋ New environment</button>}</div>
      {error && <div className="error-banner">{error}<button onClick={() => setError("")}>Dismiss</button></div>}{notice && <div className="notice-banner">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
      {tab === "overview" && <Overview envs={envs} jobs={jobs} events={events} overview={overview} onNavigate={setTab} />}
      {tab === "environments" && <EnvironmentTable envs={envs} busy={busy} onStop={stopEnvironment} onDelete={removeEnvironment} onExec={setExecEnv} />}
      {tab === "jobs" && <JobTable jobs={jobs} />}
      {tab === "activity" && <EventTable events={events} />}
    </div></main>
    {createOpen && <CreateDialog templates={templates} busy={busy} onClose={() => setCreateOpen(false)} onSubmit={createEnvironment} />}
    {execEnv && <ExecDialog env={execEnv} busy={busy} onClose={() => setExecEnv(null)} onSubmit={runCommand} />}
  </div>;
}

function Overview({ envs, jobs, events, overview, onNavigate }: { envs: Env[]; jobs: Job[]; events: Event[]; overview: Record<string, unknown> | null; onNavigate: (tab: Tab) => void }) {
  const alertCount = events.filter(e => e.severity === "critical" || e.severity === "warn").length;
  const states = Object.entries((overview?.envs_by_state ?? {}) as Record<string, number>);
  const isolation = overview?.isolation && typeof overview.isolation === "object" ? overview.isolation as Record<string, unknown> : null;
  const runtime = typeof isolation?.runtime === "string" ? isolation.runtime : "Unavailable";
  const degraded = isolation?.degraded === true;
  return <><section className="metrics-grid"><Metric label="Environments" value={envs.length} sub={`${envs.filter(e => e.observed_state === "running").length} running`} tone="blue" icon="▦" />
    <Metric label="Active jobs" value={jobs.filter(j => ["queued", "running"].includes(j.status)).length} sub={`${jobs.filter(j => j.status === "queued").length} queued`} tone="violet" icon="⌘" />
    <Metric label="Alerts" value={alertCount} sub="In recent activity" tone={alertCount ? "amber" : "green"} icon="⚑" />
    <Metric label="Isolation" value={runtime} sub={overview ? degraded ? "Degraded mode enabled" : "Configured · host proof pending" : "Admin API data unavailable"} tone={degraded ? "amber" : "green"} icon="⛨" /></section>
    <div className="dashboard-grid"><section className="panel span-2"><PanelTitle title="Environments" action="View all" onAction={() => onNavigate("environments")} />
      {envs.length ? <EnvironmentTable envs={envs.slice(0, 5)} busy={false} compact onStop={() => undefined} onDelete={() => undefined} onExec={() => undefined} /> : <Empty title="No environments yet" text="Create an environment when the runner and approved sandbox images are available." />}</section>
      <section className="panel"><PanelTitle title="Recent activity" action="View all" onAction={() => onNavigate("activity")} />{events.length ? <EventList events={events.slice(0, 6)} /> : <Empty title="No activity recorded" text="API activity will appear here when available." />}</section>
      <section className="panel span-2"><PanelTitle title="Recent jobs" action="View jobs" onAction={() => onNavigate("jobs")} />{jobs.length ? <JobTable jobs={jobs.slice(0, 5)} compact /> : <Empty title="No jobs yet" text="Execution jobs appear after they are submitted through the API." />}</section>
      <section className="panel"><PanelTitle title="Host allocation" />{overview ? <div className="host-facts">{states.map(([state, count]) => <div key={state}><span>{state}</span><b>{count}</b></div>)}<small>Runtime configuration is reported by the API; runsc isolation is not host-verified.</small></div> : <Empty title="Admin data unavailable" text="Host allocation is shown to admins when the API permits it." />}</section>
    </div></>;
}

function Metric({ label, value, sub, tone, icon }: { label: string; value: string | number; sub: string; tone: string; icon: string }) { return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><p>{label}</p><strong>{value}</strong><small>{sub}</small></article>; }
function PanelTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) { return <div className="panel-title"><h2>{title}</h2>{action && <button className="text-button" onClick={onAction}>{action} →</button>}</div>; }
function Empty({ title, text }: { title: string; text: string }) { return <div className="empty"><span>◇</span><strong>{title}</strong><p>{text}</p></div>; }
function EnvironmentTable({ envs, busy, compact = false, onStop, onDelete, onExec }: { envs: Env[]; busy: boolean; compact?: boolean; onStop: (env: Env) => void; onDelete: (env: Env) => void; onExec: (env: Env) => void }) {
  if (!envs.length) return <Empty title="No environments found" text="Environment state will appear here when returned by the API." />;
  return <div className="table-wrap"><table><thead><tr><th>Environment</th><th>Template</th><th>Status</th>{!compact && <><th>Size</th><th>Isolation tier</th></>}<th>Created resource</th>{!compact && <th>Actions</th>}</tr></thead><tbody>{envs.map(env => <tr key={env.id}><td><div className="env-name"><span className="env-glyph">▦</span><span><b>{env.name}</b><small>{env.id.slice(0, 8)}</small></span></div></td><td>{env.template}</td><td><Badge value={env.observed_state} /></td>{!compact && <><td>{env.size}</td><td>{env.isolation_tier || "pending"}</td></>}<td>{env.cpu_millis}m CPU · {env.mem_mb} MB</td>{!compact && <td><div className="row-actions"><button disabled={busy || env.desired_state !== "running"} onClick={() => onExec(env)}>Exec</button><button disabled={busy || env.desired_state !== "running"} onClick={() => onStop(env)}>Stop</button><button disabled={busy} onClick={() => onDelete(env)}>Delete</button></div></td>}</tr>)}</tbody></table></div>;
}
function JobTable({ jobs, compact = false }: { jobs: Job[]; compact?: boolean }) { if (!jobs.length) return <Empty title="No jobs found" text="Jobs and their actual API results will appear here." />; return <div className="table-wrap"><table><thead><tr><th>Job</th><th>Kind</th><th>Status</th><th>Environment</th><th>Created</th>{!compact && <th>Result</th>}</tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td><code>{j.id.slice(0, 8)}</code></td><td>{j.kind}</td><td><Badge value={j.status} /></td><td><code>{j.env_id.slice(0, 8)}</code></td><td>{date(j.created_at)}</td>{!compact && <td className="result-cell">{j.result?.output ? String(j.result.output).slice(0, 100) : j.status === "queued" || j.status === "running" ? "Waiting for runner" : JSON.stringify(j.result ?? {})}</td>}</tr>)}</tbody></table></div>; }
function EventTable({ events }: { events: Event[] }) { if (!events.length) return <Empty title="No activity found" text="Events are loaded from the authenticated API." />; return <div className="panel"><EventList events={events} /></div>; }
function EventList({ events }: { events: Event[] }) { return <div className="event-list">{events.map(e => <article className="event-item" key={e.id}><span className={`event-mark ${e.severity}`}>•</span><div><b>{e.kind.replaceAll(".", " · ")}</b><p>{e.message}</p><small>{date(e.ts)} {e.env_id ? `· ${e.env_id.slice(0, 8)}` : ""}</small></div></article>)}</div>; }
function Badge({ value }: { value: string }) { return <span className={`badge ${value.toLowerCase().replaceAll("_", "-")}`}>{value.replaceAll("_", " ")}</span>; }
function date(value: string) { const parsed = new Date(value); return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString(); }
function isActivityEvent(value: unknown): value is Event {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return typeof item.id === "number" && typeof item.ts === "string"
    && (item.severity === "info" || item.severity === "warn" || item.severity === "critical")
    && typeof item.kind === "string" && typeof item.message === "string"
    && (item.env_id === null || typeof item.env_id === "string");
}

function CreateDialog({ templates, busy, onClose, onSubmit }: { templates: Array<{ name: string; title: string; sizes: string[] }>; busy: boolean; onClose: () => void; onSubmit: (name: string, template: string, size: string) => void }) {
  const [name, setName] = useState(""); const [template, setTemplate] = useState("app-target"); const [size, setSize] = useState("S");
  const selected = templates.find(t => t.name === template);
  return <Dialog title="Create environment" onClose={onClose}><form className="form-stack" onSubmit={e => { e.preventDefault(); onSubmit(name, template, size); }}>
    <p className="muted">This sends a real request to the API. Provisioning requires a configured runner and locally available approved images.</p>
    <label>Name<input required maxLength={64} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. incident-review" /></label>
    <label>Template<select value={template} onChange={e => setTemplate(e.target.value)}>{templates.map(t => <option key={t.name} value={t.name}>{t.title} ({t.name})</option>)}</select></label>
    <label>Size<select value={size} onChange={e => setSize(e.target.value)}>{(selected?.sizes ?? ["S", "M", "L"]).map(s => <option key={s}>{s}</option>)}</select></label>
    <div className="dialog-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy || !templates.length}>{busy ? "Submitting…" : "Request environment"}</button></div>
  </form></Dialog>;
}
function ExecDialog({ env, busy, onClose, onSubmit }: { env: Env; busy: boolean; onClose: () => void; onSubmit: (env: Env, command: string) => void }) {
  const [command, setCommand] = useState("");
  return <Dialog title={`Run command · ${env.name}`} onClose={onClose}><form className="form-stack" onSubmit={e => { e.preventDefault(); onSubmit(env, command); }}><p className="muted">Commands are sent to the toolbox through R17 and run only if the API reports the environment is running.</p><label>Command<input required maxLength={4096} value={command} onChange={e => setCommand(e.target.value)} placeholder="whoami" /></label><div className="dialog-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy}>{busy ? "Queueing…" : "Queue command"}</button></div></form></Dialog>;
}
function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) { return <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><section className="modal" role="dialog" aria-modal="true" aria-label={title}><div className="modal-head"><h2>{title}</h2><button className="icon-button" aria-label="Close" onClick={onClose}>×</button></div>{children}</section></div>; }

export default App;
