import { useCallback, useEffect, useState } from "react";
import { api, type Env, type Event, type Job, type Team, type User } from "../api";

function isActivityEvent(value: unknown): value is Event {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  return typeof item.id === "number" && typeof item.ts === "string"
    && (item.severity === "info" || item.severity === "warn" || item.severity === "critical")
    && typeof item.kind === "string" && typeof item.message === "string"
    && (item.env_id === null || typeof item.env_id === "string");
}

export function useConsoleData(user: User | null) {
  const [envs, setEnvs] = useState<Env[]>([]); const [jobs, setJobs] = useState<Job[]>([]);
  const [events, setEvents] = useState<Event[]>([]); const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]); const [templates, setTemplates] = useState<Array<{ name: string; title: string; sizes: string[] }>>([]);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [streamLive, setStreamLive] = useState(false); const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!user) return;
    setError("");
    try {
      const [envPage, jobPage, eventPage, teamPage, userPage, adminData] = await fetchDashboard(user.role);
      setEnvs(envPage.items); setJobs(jobPage.items); setEvents(eventPage.items); setTeams(teamPage.items);
      setUsers(userPage.items); setOverview(adminData);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not load console data"); }
  }, [user]);

  useEffect(() => { api.health().then(value => setHealth(value.db ? "ok" : "down")).catch(() => setHealth("down")); }, []);
  useEffect(() => {
    if (!user) return;
    void load();
    api.templates().then(page => setTemplates(page.items)).catch(cause => setError(cause.message));
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [user, load]);
  useActivityStream(user, setEvents, setStreamLive);
  return { envs, jobs, events, teams, users, templates, overview, health, streamLive, error, setError, load };
}

async function fetchDashboard(role: string) {
  const jobs = role === "analyst" || role === "team_lead" ? api.jobs() : Promise.resolve({ items: [], next_cursor: null });
  const users = ["admin", "auditor", "team_lead"].includes(role) ? api.users() : Promise.resolve({ items: [], next_cursor: null });
  const admin = ["admin", "auditor"].includes(role) ? api.overview() : Promise.resolve(null);
  return Promise.all([api.envs(), jobs, api.events(), api.teams(), users, admin]);
}

function useActivityStream(user: User | null, setEvents: (update: (events: Event[]) => Event[]) => void, setLive: (value: boolean) => void) {
  useEffect(() => {
    if (!user) { setLive(false); return; }
    const stream = api.activityStream();
    const onActivity = (raw: globalThis.Event) => {
      let value: unknown;
      try { value = JSON.parse((raw as MessageEvent<string>).data) as unknown; } catch { return; }
      if (isActivityEvent(value)) setEvents(previous => [value, ...previous.filter(event => event.id !== value.id)].slice(0, 200));
    };
    stream.addEventListener("open", () => setLive(true));
    stream.addEventListener("error", () => setLive(false));
    stream.addEventListener("activity", onActivity);
    return () => { stream.close(); setLive(false); };
  }, [user, setEvents, setLive]);
}
