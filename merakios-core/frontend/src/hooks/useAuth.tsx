import { useState, useEffect, createContext, useContext, ReactNode } from "react";
import { api } from "@/services/api";

interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session
    const stored = localStorage.getItem("meraki_session");
    if (stored) {
      try {
        const { user } = JSON.parse(stored);
        setUser(user);
      } catch (e) {
        localStorage.removeItem("meraki_session");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, pass: string) => {
    try {
      const data = await api.login(email, pass);
      localStorage.setItem("meraki_session", JSON.stringify({
        access_token: data.access_token,
        user: data.user
      }));
      setUser(data.user);
    } catch (err) {
      console.error(err);
      throw new Error("Credenciales inválidas");
    }
  };

  const signOut = () => {
    localStorage.removeItem("meraki_session");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
