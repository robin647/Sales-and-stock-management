import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "../api/endpoints";

const AuthContext = createContext(null);

function decodeToken(token) {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return decoded;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      const decoded = decodeToken(token);
      if (decoded) {
        setUser({
          id: decoded.user_id || decoded.showroom_id,
          role: decoded.role,
          showroomId: decoded.showroom_id,
          showroomName: decoded.showroom_name,
          fullName: decoded.full_name,
        });
      }
    }
    setLoading(false);
  }, []);

  // Listen for showroom login events
  useEffect(() => {
    function handleLoginSuccess() {
      const token = localStorage.getItem("access_token");
      if (token) {
        const decoded = decodeToken(token);
        if (decoded) {
          setUser({
            id: decoded.showroom_id,
            role: decoded.role || "showroom",
            showroomId: decoded.showroom_id,
            showroomName: decoded.showroom_name,
            fullName: decoded.showroom_name,
          });
        }
      }
    }

    window.addEventListener("loginSuccess", handleLoginSuccess);
    return () => window.removeEventListener("loginSuccess", handleLoginSuccess);
  }, []);

  async function login(username, password) {
    const { data } = await authApi.login(username, password);
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    const decoded = decodeToken(data.access);
    setUser({
      id: decoded.user_id,
      role: decoded.role,
      showroomId: decoded.showroom_id,
      showroomName: decoded.showroom_name,
      fullName: decoded.full_name,
    });
    return decoded;
  }

  function logout() {
    localStorage.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAdmin: user?.role === "admin" }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
