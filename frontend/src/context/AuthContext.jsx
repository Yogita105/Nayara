import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, setCsrfToken } from "../lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (credentials) => {
    const { data } = await api.post("/auth/login", credentials);
    setCsrfToken(data.csrf_token);
    setUser(data.user);
    return data.user;
  };

  const register = async (details) => {
    const { data } = await api.post("/auth/register", details);
    setCsrfToken(data.csrf_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    await api.post("/auth/logout");
    setCsrfToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, checkAuth, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
