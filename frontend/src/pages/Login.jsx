import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { authApi } from "../api/endpoints.js";

export default function Login() {
  const [loginMode, setLoginMode] = useState("admin"); // "admin" or "showroom"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (loginMode === "admin") {
        await login(username, password);
      } else {
        // Showroom login
        await loginShowroom(username, password);
      }
      navigate("/");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Login failed. Please check your username and password."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loginShowroom(username, password) {
    const { data } = await authApi.showroomLogin(username, password);
    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);
    
    // Decode token to get showroom info
    const decoded = decodeToken(data.access);
    window.dispatchEvent(new Event("loginSuccess"));
  }

  function decodeToken(token) {
    try {
      const payload = token.split(".")[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
      return decoded;
    } catch {
      return null;
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <h1 className="text-xl font-semibold text-brand-700 mb-1">Mahir Sherwani</h1>
        <p className="text-sm text-gray-500 mb-6">Showroom Stock &amp; Sales Management</p>

        {/* Login Mode Toggle */}
        <div className="mb-6 flex gap-2">
          <button
            type="button"
            onClick={() => setLoginMode("admin")}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              loginMode === "admin"
                ? "bg-brand-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Admin
          </button>
          <button
            type="button"
            onClick={() => setLoginMode("showroom")}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              loginMode === "showroom"
                ? "bg-brand-500 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            Showroom
          </button>
        </div>

        {error && (
          <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
        <input
          className="w-full mb-4 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />

        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <input
          type="password"
          className="w-full mb-6 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2 rounded-lg disabled:opacity-60"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
