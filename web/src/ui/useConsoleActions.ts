import { useCallback, useState } from "react";
import { api, type Env, type Team, type User } from "../api";

type Quotas = Pick<Team, "quota_envs" | "quota_cpu_millis" | "quota_mem_mb" | "quota_storage_mb">;
type ActionsInput = { csrf: string; load: () => Promise<void>; navigate: (tab: "jobs") => void; setError: (message: string) => void; setNotice: (message: string) => void; closeCreate: () => void; closeExec: () => void };

export function useConsoleActions(input: ActionsInput) {
  const [busy, setBusy] = useState(false);
  const perform = useMutation(input.load, input.setError, input.setNotice, setBusy);
  const createEnvironment = async (name: string, template: string, size: string) => {
    const ok = await perform("Environment request submitted.", () => api.createEnv(input.csrf, { name, template, size }));
    if (ok) input.closeCreate();
  };
  const stopEnvironment = (env: Env) => perform(`Stop requested for ${env.name}.`, () => api.stopEnv(input.csrf, env.id));
  const removeEnvironment = async (env: Env) => {
    if (window.confirm(`Request deletion of “${env.name}”?`)) await perform(`Deletion requested for ${env.name}.`, () => api.deleteEnv(input.csrf, env.id));
  };
  const runCommand = async (env: Env, command: string) => {
    const ok = await perform("Command queued. Results appear when the runner finishes it.", () => api.exec(input.csrf, env.id, command));
    if (ok) { input.closeExec(); input.navigate("jobs"); }
  };
  const createUser = (body: { email: string; password: string; role: string; team_id: string | null }) => perform("User created.", () => api.createUser(input.csrf, body));
  const setUserDisabled = (target: User) => perform(`User ${target.disabled ? "enabled" : "disabled"}.`, () => api.updateUser(input.csrf, target.id, { disabled: !target.disabled }));
  const createTeam = (name: string) => perform(`Team ${name} created.`, () => api.createTeam(input.csrf, { name }));
  const updateTeam = (team: Team, quota: Quotas) => perform(`Quota updated for ${team.name}.`, () => api.updateTeam(input.csrf, team.id, quota));
  const killSwitch = () => requestKillSwitch(input.csrf, perform);
  return { busy, createEnvironment, stopEnvironment, removeEnvironment, runCommand, createUser, setUserDisabled, createTeam, updateTeam, killSwitch };
}

function useMutation(load: () => Promise<void>, setError: (message: string) => void, setNotice: (message: string) => void, setBusy: (busy: boolean) => void) {
  return useCallback(async (message: string, action: () => Promise<unknown>): Promise<boolean> => {
    setBusy(true); setError("");
    try { await action(); setNotice(message); await load(); return true; }
    catch (cause) { setError(cause instanceof Error ? cause.message : "API request failed"); return false; }
    finally { setBusy(false); }
  }, [load, setBusy, setError, setNotice]);
}

async function requestKillSwitch(csrf: string, perform: (message: string, action: () => Promise<unknown>) => Promise<boolean>) {
  if (!window.confirm("Set every running environment to stopped? The runner will perform the actual stop.")) return;
  await perform("Kill switch request recorded.", () => api.killSwitch(csrf));
}
