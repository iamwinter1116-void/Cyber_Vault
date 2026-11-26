import { useEffect, useState } from "react";
import { api, type User } from "../api";

export function useSession() {
  const [user, setUser] = useState<User | null>(null);
  const [csrf, setCsrf] = useState("");
  const [checked, setChecked] = useState(false);
  const [apiAvailable, setApiAvailable] = useState(false);

  useEffect(() => {
    let active = true;
    api.health().then(health => { if (active) setApiAvailable(health.db); }).catch(() => { if (active) setApiAvailable(false); });
    api.me().then(session => {
      if (active) { setUser(session.user); setCsrf(session.csrf_token); }
    }).catch(() => { if (active) { setUser(null); setCsrf(""); } }).finally(() => { if (active) setChecked(true); });
    return () => { active = false; };
  }, []);

  async function signIn(email: string, password: string) {
    const login = await api.login(email, password);
    const session = await api.me();
    if (login.user.id !== session.user.id) throw new Error("The API session does not match the signed-in account");
    setUser(session.user); setCsrf(session.csrf_token);
  }

  async function signOut() {
    await api.logout(csrf);
    setUser(null); setCsrf("");
  }

  return { user, csrf, checked, apiAvailable, signIn, signOut };
}
