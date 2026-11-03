import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearLocal, getTokens, onAuthChange, setTokens } from "./api";

const AuthCtx = createContext(null);

export function applyTheme(theme) {
  const root = document.documentElement;
  if (!theme || theme === "auto") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try { localStorage.setItem("ruvia-theme", theme || "auto"); } catch { /* ignore */ }
  const dark = theme === "dark" || ((!theme || theme === "auto") && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute("content", dark ? "#0E1B20" : "#ECEFE6"));
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getTokens()?.user || null);
  const [ready, setReady] = useState(!getTokens());

  useEffect(() => onAuthChange((t) => { if (!t) setUser(null); }), []);

  const loadMe = useCallback(async () => {
    try {
      const me = await api("/me/");
      setUser(me);
      setTokens({ ...getTokens(), user: me });
      applyTheme(me.theme);
      return me;
    } catch (e) {
      if (e.status === 401) setUser(null);
      return null;
    } finally { setReady(true); }
  }, []);

  useEffect(() => { if (getTokens()) loadMe(); }, [loadMe]);

  const signIn = useCallback((data) => {
    setTokens({ access: data.access, refresh: data.refresh, user: data.user });
    setUser(data.user);
    applyTheme(data.user?.theme);
  }, []);

  const signOut = useCallback(async () => {
    const t = getTokens();
    try { await api("/auth/logout/", { method: "POST", body: { refresh: t?.refresh } }); } catch { /* ignore */ }
    await clearLocal();
    navigator.serviceWorker?.controller?.postMessage("clear-api-cache");
    setTokens(null);
    setUser(null);
  }, []);

  const update = useCallback(async (patch) => {
    const me = await api("/me/", { method: "PATCH", body: patch });
    setUser(me);
    setTokens({ ...getTokens(), user: me });
    if ("theme" in patch) applyTheme(me.theme);
    return me;
  }, []);

  const value = useMemo(() => ({ user, ready, signIn, signOut, update, reload: loadMe }), [user, ready, signIn, signOut, update, loadMe]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
