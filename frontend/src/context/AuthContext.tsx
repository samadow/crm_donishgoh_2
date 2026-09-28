import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api/client";
import { User } from "../types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  reloadUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadUser = async () => {
    if (!localStorage.getItem("orion_access")) {
      setUser(null);
      return;
    }
    try {
      setUser(await apiRequest<User>("/auth/me/"));
    } catch {
      localStorage.removeItem("orion_access");
      localStorage.removeItem("orion_refresh");
      setUser(null);
    }
  };

  useEffect(() => {
    reloadUser().finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    login: async (email, password) => {
      const data = await apiRequest<{ access: string; refresh: string; user: User }>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("orion_access", data.access);
      localStorage.setItem("orion_refresh", data.refresh);
      setUser(data.user);
      return data.user;
    },
    logout: () => {
      localStorage.removeItem("orion_access");
      localStorage.removeItem("orion_refresh");
      setUser(null);
    },
    reloadUser,
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

