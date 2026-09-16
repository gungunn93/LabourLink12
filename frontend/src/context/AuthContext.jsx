import React, { createContext, useContext, useMemo, useState } from "react";
import api, { unwrap, messageOf } from "../services/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("ll_user") || "null"));
  const [token, setToken] = useState(() => localStorage.getItem("ll_token"));

  const persist = (nextUser, nextToken) => {
    setUser(nextUser);
    setToken(nextToken);
    if (nextUser && nextToken) {
      localStorage.setItem("ll_user", JSON.stringify(nextUser));
      localStorage.setItem("ll_token", nextToken);
    } else {
      localStorage.removeItem("ll_user");
      localStorage.removeItem("ll_token");
    }
  };

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    const data = unwrap(res);
    persist(data.user, data.token);
    return data.user;
  };

  const logout = () => persist(null, null);

  const value = useMemo(() => ({ user, token, login, logout, persist, messageOf }), [user, token]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
