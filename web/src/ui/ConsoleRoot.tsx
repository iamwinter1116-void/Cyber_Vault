import { useCallback, useEffect, useState } from "react";
import { AuditPage } from "./AuditPage";
import { CreateDialog, EnvironmentTable, EventTable, ExecDialog, JobTable, Login, Overview } from "./AppComponents";
import { TeamsPage, UsersPage } from "./AdminPages";
import { WorkloadPage } from "./WorkloadPage";
import { useConsoleActions } from "./useConsoleActions";
import { useConsoleData } from "./useConsoleData";
import { useSession } from "./useSession";
import { sandboxActionsEnabled, type Env, type User } from "../api";

type Tab = "overview" | "environments" | "jobs" | "files" | "ai-redteam" | "activity" | "users" | "teams" | "audit";
type NavItem = { id: Tab; label: string; glyph: string };

function tabFromPath(path: string): Tab {
  if (path.startsWith("/admin/teams")) return "teams";
  if (path.startsWith("/admin/users") || path === "/users") return "users";
  if (path.startsWith("/audit")) return "audit";
  if (path.startsWith("/files")) return "files";
  if (path.startsWith("/ai-redteam")) return "ai-redteam";
  if (path.startsWith("/envs")) return "environments";
  if (path.startsWith("/jobs")) return "jobs";
  if (path.startsWith("/activity")) return "activity";
  return "overview";
}

function pathForTab(tab: Tab): string {
  return ({ overview: "/", environments: "/envs", jobs: "/jobs", files: "/files", "ai-redteam": "/ai-redteam", activity: "/activity", users: "/admin/users", teams: "/admin/teams", audit: "/audit" })[tab];
}

export default function ConsoleRoot() {
  const session = useSession(); const data = useConsoleData(session.user);
  const [tab, setTab] = useState<Tab>(() => tabFromPath(window.location.pathname));
  const [notice, setNotice] = useState(""); const [createOpen, setCreateOpen] = useState(false); const [execEnv, setExecEnv] = useState<Env | null>(null);
  const navigate = useCallback((destination: Tab) => { setTab(destination); window.history.pushState({}, "", pathForTab(destination)); }, []);
  const actions = useConsoleActions({ csrf: session.csrf, load: data.load, navigate, setError: data.setError, setNotice, closeCreate: () => setCreateOpen(false), closeExec: () => setExecEnv(null) });
  useRouteState(session.user, tab, setTab, navigate);
  async function signOut() {
    try { await session.signOut(); navigate("overview"); window.history.replaceState({}, "", "/login"); }
    catch (cause) { data.setError(cause instanceof Error ? cause.message : "Could not sign out"); }
  }
  if (!session.checked) return <main className="login-page"><section className="login-card"><div className="brand-mark">A</div><p className="eyebrow">SECURITY OPERATIONS</p><h1>ABHEDYA</h1><p className="muted">Checking your API session…</p></section></main>;
  if (!session.user) return <Login apiAvailable={session.apiAvailable} onLogin={async (email, password) => { await session.signIn(email, password); navigate("environments"); }} />;
  return <ConsoleView user={session.user} csrf={session.csrf} data={data} actions={actions} tab={tab} navigate={navigate} notice={notice} setNotice={setNotice} signOut={signOut} createOpen={createOpen} setCreateOpen={setCreateOpen} execEnv={execEnv} setExecEnv={setExecEnv} />;
}

function useRouteState(user: User | null, tab: Tab, setTab: (value: Tab) => void, navigate: (destination: Tab) => void) {
  useEffect(() => {
    const handlePath = () => setTab(tabFromPath(window.location.pathname));
    window.addEventListener("popstate", handlePath);
    return () => window.removeEventListener("popstate", handlePath);
  }, [setTab]);
  useEffect(() => {
    if (!user) return;
    const allowed = tab === "teams" || tab === "environments" || tab === "activity" || tab === "overview"
      || (tab === "jobs" && ["analyst", "team_lead"].includes(user.role))
      || ((tab === "files" || tab === "ai-redteam") && ["analyst", "team_lead"].includes(user.role))
      || ((tab === "users" || tab === "audit") && ["admin", "auditor", "team_lead"].includes(user.role));
    if (!allowed) navigate("overview");
    else if (window.location.pathname === "/login") window.history.replaceState({}, "", pathForTab(tab));
  }, [user, tab, navigate]);
}

type ConsoleData = ReturnType<typeof useConsoleData>;
type ConsoleActions = ReturnType<typeof useConsoleActions>;

function ConsoleView({ user, csrf, data, actions, tab, navigate, notice, setNotice, signOut, createOpen, setCreateOpen, execEnv, setExecEnv }: {
  user: User; csrf: string; data: ConsoleData; actions: ConsoleActions; tab: Tab; navigate: (tab: Tab) => void;
  notice: string; setNotice: (value: string) => void; signOut: () => Promise<void>; createOpen: boolean;
  setCreateOpen: (value: boolean) => void; execEnv: Env | null; setExecEnv: (value: Env | null) => void;
}) {
  const nav = navigationFor(user); const tamperAlert = data.events.find(event => event.kind === "alert.tamper_detected");
  return <div className="app-shell"><Sidebar nav={nav} tab={tab} user={user} health={data.health} jobs={data.jobs} navigate={navigate} signOut={signOut} />
    <main className="main-area"><ConsoleHeader tab={tab} nav={nav} streamLive={data.streamLive} refresh={data.load} />
      <PageContent user={user} data={data} actions={actions} tab={tab} nav={nav} navigate={navigate} notice={notice} setNotice={setNotice} tamperMessage={tamperAlert?.message} openCreate={() => setCreateOpen(true)} openExec={setExecEnv} csrf={csrf} />
    </main>
    {createOpen && <CreateDialog templates={data.templates} busy={actions.busy} onClose={() => setCreateOpen(false)} onSubmit={actions.createEnvironment} />}
    {execEnv && <ExecDialog env={execEnv} busy={actions.busy} onClose={() => setExecEnv(null)} onSubmit={actions.runCommand} />}
  </div>;
}

function navigationFor(user: User): NavItem[] {
  return [
    { id: "overview", label: "Overview", glyph: "⌂" }, { id: "environments", label: "Environments", glyph: "▦" },
    ...( ["analyst", "team_lead"].includes(user.role) ? [{ id: "jobs" as const, label: "Jobs", glyph: "⌘" }] : []),
    ...( ["analyst", "team_lead"].includes(user.role) ? [{ id: "files" as const, label: "File analysis", glyph: "▧" }, { id: "ai-redteam" as const, label: "AI red team", glyph: "✳" }] : []),
    { id: "activity", label: "Activity", glyph: "◷" }, { id: "teams", label: "Teams", glyph: "♙" },
    ...( ["admin", "auditor", "team_lead"].includes(user.role) ? [{ id: "users" as const, label: "Users", glyph: "♧" }, { id: "audit" as const, label: "Audit", glyph: "▤" }] : []),
  ];
}

function Sidebar({ nav, tab, user, health, jobs, navigate, signOut }: { nav: NavItem[]; tab: Tab; user: User; health: "checking" | "ok" | "down"; jobs: ConsoleData["jobs"]; navigate: (tab: Tab) => void; signOut: () => Promise<void> }) {
  return <aside className="sidebar"><a className="brand" href="/" onClick={event => { event.preventDefault(); navigate("overview"); }}><span className="brand-mark small">A</span><span>ABHEDYA<small>SECURITY PLATFORM</small></span></a>
    <p className="nav-label">WORKSPACE</p><nav>{nav.map(item => <button key={item.id} className={tab === item.id ? "nav-item selected" : "nav-item"} onClick={() => navigate(item.id)}><span>{item.glyph}</span>{item.label}{item.id === "jobs" && jobs.some(job => job.status === "queued") && <i className="nav-dot" />}</button>)}</nav>
    <div className="sidebar-bottom"><div className="host-status"><span className={`status-dot ${health}`} />API {health === "ok" ? "connected" : health === "down" ? "unavailable" : "checking"}</div><div className="user-mini"><div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div><div className="user-label">{user.email}<small>{user.role.replace("_", " ")}</small></div><button className="icon-button" title="Sign out" onClick={() => void signOut()}>↗</button></div></div>
  </aside>;
}

function ConsoleHeader({ tab, nav, streamLive, refresh }: { tab: Tab; nav: NavItem[]; streamLive: boolean; refresh: () => Promise<void> }) {
  return <header className="topbar"><div><span className="breadcrumb">Console</span><span className="slash">/</span><strong>{nav.find(item => item.id === tab)?.label}</strong></div><div className="top-actions"><span className="local-tag"><span className={`status-dot ${streamLive ? "ok" : "down"}`} />ACTIVITY {streamLive ? "STREAM LIVE" : "RECONNECTING"}</span><button className="icon-button refresh" title="Refresh data" onClick={() => void refresh()}>↻</button></div></header>;
}

function PageContent({ user, data, actions, tab, nav, navigate, notice, setNotice, tamperMessage, openCreate, openExec, csrf }: {
  user: User; data: ConsoleData; actions: ConsoleActions; tab: Tab; nav: NavItem[]; navigate: (tab: Tab) => void;
  notice: string; setNotice: (value: string) => void; tamperMessage?: string; openCreate: () => void; openExec: (env: Env) => void; csrf: string;
}) {
  const title = tab === "overview" ? "Security overview" : nav.find(item => item.id === tab)?.label ?? "Console";
  return <div className="content"><div className="page-heading"><div><p className="eyebrow">OPERATIONS / {tab.toUpperCase()}</p><h1>{title}</h1><p className="muted">{tab === "overview" ? "Live view of your ABHEDYA workspace." : "Data loaded from the authenticated ABHEDYA API."}</p></div>{tab === "environments" && <button className="primary" disabled={!sandboxActionsEnabled} onClick={openCreate}>Create</button>}</div>
    {data.error && <div className="error-banner">{data.error}<button onClick={() => data.setError("")}>Dismiss</button></div>}
    {notice && <div className="notice-banner">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div>}
    {tab === "environments" && !sandboxActionsEnabled && <div className="notice-banner" role="status">Local website demo: sandbox create, stop, delete, and exec actions are disabled. Enable them only after a real runner and approved sandbox images are available.</div>}
    {tamperMessage && <div className="tamper-banner" role="alert"><strong>Audit tampering detected</strong><span>{tamperMessage}</span></div>}
    {tab === "overview" && <Overview envs={data.envs} jobs={data.jobs} events={data.events} overview={data.overview} onNavigate={navigate} canViewJobs={["analyst", "team_lead"].includes(user.role)} onKillSwitch={user.role === "admin" ? actions.killSwitch : undefined} />}
    {tab === "environments" && <EnvironmentTable envs={data.envs} busy={actions.busy} actionsEnabled={sandboxActionsEnabled} onStop={actions.stopEnvironment} onDelete={actions.removeEnvironment} onExec={openExec} />}
    {tab === "jobs" && <JobTable jobs={data.jobs} />}{tab === "activity" && <EventTable events={data.events} />}
    {tab === "files" && <WorkloadPage kind="file_analysis" jobs={data.jobs} />}
    {tab === "ai-redteam" && <WorkloadPage kind="ai_scan" jobs={data.jobs} />}
    {tab === "users" && <UsersPage users={data.users} teams={data.teams} canManage={user.role === "admin"} onCreate={actions.createUser} onDisable={actions.setUserDisabled} />}
    {tab === "teams" && <TeamsPage teams={data.teams} canManage={user.role === "admin"} onCreate={actions.createTeam} onUpdate={actions.updateTeam} />}
    {tab === "audit" && <AuditPage csrf={csrf} canVerify={user.role === "admin" || user.role === "auditor"} onError={data.setError} />}
  </div>;
}
