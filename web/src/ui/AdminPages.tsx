import { useState } from "react";
import type { Team, User } from "../api";

type UserPageProps = { users: User[]; teams: Team[]; canManage: boolean; onCreate: (body: { email: string; password: string; role: string; team_id: string | null }) => Promise<boolean>; onDisable: (user: User) => Promise<boolean> };

export function UsersPage({ users, teams, canManage, onCreate, onDisable }: UserPageProps) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [role, setRole] = useState("analyst"); const [teamId, setTeamId] = useState("");
  const needsTeam = role === "analyst" || role === "team_lead";
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await onCreate({ email, password, role, team_id: needsTeam ? teamId : null })) { setEmail(""); setPassword(""); }
  }
  return <div className="dashboard-grid admin-grid"><section className="panel span-2"><PanelTitle title="Users in scope" /><TableWrap>
    <table><thead><tr><th>Email</th><th>Role</th><th>Team</th><th>State</th>{canManage && <th>Action</th>}</tr></thead><tbody>
      {users.map(user => <tr key={user.id}><td>{user.email}</td><td>{user.role.replace("_", " ")}</td><td>{teams.find(t => t.id === user.team_id)?.name ?? "Platform"}</td><td><Badge value={user.disabled ? "disabled" : "enabled"} /></td>
        {canManage && <td><button className="secondary small-button" onClick={() => void onDisable(user)}>{user.disabled ? "Enable" : "Disable"}</button></td>}</tr>)}
    </tbody></table>
  </TableWrap></section>
  {canManage && <section className="panel"><PanelTitle title="Create user" /><form className="form-stack" onSubmit={submit}>
    <label>Email<input name="email" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label>Temporary password<input name="password" type="password" minLength={12} maxLength={256} required value={password} onChange={e => setPassword(e.target.value)} /></label>
    <label>Role<select value={role} onChange={e => setRole(e.target.value)}><option value="analyst">Analyst</option><option value="team_lead">Team lead</option><option value="auditor">Auditor</option><option value="admin">Admin</option></select></label>
    {needsTeam && <label>Team<select required value={teamId} onChange={e => setTeamId(e.target.value)}><option value="">Choose a team</option>{teams.map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label>}
    <button className="primary">Create</button>
  </form></section>}
  {!users.length && <EmptyState text="The API returned no users." />}</div>;
}

type TeamQuotas = Pick<Team, "quota_envs" | "quota_cpu_millis" | "quota_mem_mb" | "quota_storage_mb">;
type TeamPageProps = { teams: Team[]; canManage: boolean; onCreate: (name: string) => Promise<boolean>; onUpdate: (team: Team, quota: TeamQuotas) => Promise<boolean> };

export function TeamsPage({ teams, canManage, onCreate, onUpdate }: TeamPageProps) {
  const [name, setName] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) { event.preventDefault(); if (await onCreate(name)) setName(""); }
  return <div className="dashboard-grid admin-grid"><section className="panel span-2"><PanelTitle title="Teams and quotas" />
    {teams.map(team => <TeamRow key={team.id} team={team} canManage={canManage} onUpdate={onUpdate} />)}
    {!teams.length && <EmptyState text="The API returned no teams." />}
  </section>
  {canManage && <section className="panel"><PanelTitle title="Create team" /><form className="form-stack" onSubmit={submit}>
    <label>Team name<input name="team" pattern="[a-z0-9-]{3,32}" required value={name} onChange={e => setName(e.target.value)} placeholder="incident-response" /></label>
    <p className="muted">The API applies its documented default quotas at creation.</p><button className="primary">Create</button>
  </form></section>}</div>;
}

function TeamRow({ team, canManage, onUpdate }: { team: Team; canManage: boolean; onUpdate: TeamPageProps["onUpdate"] }) {
  const [editing, setEditing] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const quota: TeamQuotas = {
      quota_envs: Number(form.get("quota_envs")), quota_cpu_millis: Number(form.get("quota_cpu_millis")),
      quota_mem_mb: Number(form.get("quota_mem_mb")), quota_storage_mb: Number(form.get("quota_storage_mb")),
    };
    if (await onUpdate(team, quota)) setEditing(false);
  }
  return <article className="team-card"><div className="team-card-head"><div><strong>{team.name}</strong><small>{team.usage.envs} environments · {team.usage.cpu_millis}m CPU · {team.usage.mem_mb} MB RAM · {team.usage.storage_mb} MB storage</small></div>
    {canManage && <button className="secondary small-button" onClick={() => setEditing(value => !value)}>{editing ? "Cancel" : "Change quota"}</button>}</div>
    <div className="quota-grid"><Quota label="Environments" used={team.usage.envs} limit={team.quota_envs} /><Quota label="CPU" used={team.usage.cpu_millis} limit={team.quota_cpu_millis} unit="m" /><Quota label="Memory" used={team.usage.mem_mb} limit={team.quota_mem_mb} unit="MB" /><Quota label="Storage" used={team.usage.storage_mb} limit={team.quota_storage_mb} unit="MB" /></div>
    {editing && <form className="quota-edit" onSubmit={submit}>{(["quota_envs", "quota_cpu_millis", "quota_mem_mb", "quota_storage_mb"] as const).map(key => <label key={key}>{key.replace("quota_", "").replaceAll("_", " ")}<input name={key} type="number" min="0" required defaultValue={team[key]} /></label>)}<button className="primary">Save quota</button></form>}
  </article>;
}

function Quota({ label, used, limit, unit = "" }: { label: string; used: number; limit: number; unit?: string }) {
  return <div className="quota-item"><span>{label}</span><strong>{used} / {limit} {unit}</strong></div>;
}

function PanelTitle({ title }: { title: string }) { return <div className="panel-title"><h2>{title}</h2></div>; }
function Badge({ value }: { value: string }) { return <span className={`badge ${value}`}>{value}</span>; }
function TableWrap({ children }: { children: React.ReactNode }) { return <div className="table-wrap">{children}</div>; }
function EmptyState({ text }: { text: string }) { return <div className="empty"><p>{text}</p></div>; }
