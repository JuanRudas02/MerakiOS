import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { identityApi, onUnauthorized, setAuthToken, type RegisterInput, type Session, type User, type Workspace } from "@/lib/api";

export const SESSION_KEY = "oneheavy.session";

type Status = "loading" | "authenticated" | "anonymous";

export interface AuthContextValue {
  status: Status;
  user: User | null;
  workspace: Workspace | null;
  login: (identifier: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  setWorkspace: (workspace: Workspace) => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readToken(): string | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as { token: string }).token : null;
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(SESSION_KEY, JSON.stringify({ token }));
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    /* almacenamiento no disponible: la sesión vive sólo en memoria */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);

  const clear = useCallback(() => {
    writeToken(null);
    setAuthToken(null);
    setUser(null);
    setWorkspace(null);
    setStatus("anonymous");
    queryClient.clear();
  }, [queryClient]);

  const applySession = useCallback((session: Session) => {
    writeToken(session.access_token);
    setAuthToken(session.access_token);
    setUser(session.user);
    setWorkspace(session.workspace);
    setStatus("authenticated");
  }, []);

  const refresh = useCallback(async () => {
    const me = await identityApi.me();
    setUser(me.user);
    setWorkspace(me.workspace);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    onUnauthorized(clear);
    const token = readToken();
    if (!token) {
      setStatus("anonymous");
      return () => onUnauthorized(null);
    }
    setAuthToken(token);
    refresh().catch(clear);
    return () => onUnauthorized(null);
  }, [clear, refresh]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      workspace,
      login: async (identifier, password) => applySession(await identityApi.login(identifier, password)),
      register: async (input) => applySession(await identityApi.register(input)),
      logout: clear,
      refresh,
      setWorkspace,
    }),
    [status, user, workspace, applySession, clear, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
