import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { SiteFooter } from "../components/SiteFooter.jsx";

const MODES = {
  admin: {
    label: "Admin",
    heading: "Admin sign in",
    subtext: "Manage showrooms, products, and reports.",
    userPlaceholder: "Admin username",
  },
  showroom: {
    label: "Showroom",
    heading: "Showroom sign in",
    subtext: "Use the username and password your Admin set up for your showroom.",
    userPlaceholder: "Showroom username",
  },
};

export default function Login() {
  const [mode, setMode] = useState("admin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, loginShowroom, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const copy = MODES[mode];

  function switchMode(next) {
    setMode(next);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = mode === "showroom"
        ? await loginShowroom(username, password)
        : await login(username, password);
      if (mode === "admin" && user?.role !== "admin") {
        logout();
        setError("These credentials belong to a Showroom account. Switch to the Showroom tab.");
        return;
      }
      if (mode === "showroom" && user?.role === "admin") {
        logout();
        setError("These credentials belong to the Admin account. Switch to the Admin tab.");
        return;
      }
      navigate("/");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Login failed. Please check your username and password."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-brand-200/40 blur-3xl dark:bg-brand-700/20" />
      <div className="pointer-events-none absolute -bottom-32 -right-24 h-96 w-96 rounded-full bg-indigo-200/40 blur-3xl dark:bg-indigo-700/20" />
      <div className="relative w-full max-w-md">
        <div className="login-brand text-center mb-7">
          <div className="login-brandmark inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white font-bold text-lg mb-4 shadow-lg shadow-brand-500/25">
            MS
          </div>
          <h1 className="login-title text-2xl font-bold tracking-tight">Mahir Sherwani</h1>
          <p className="login-subtitle text-sm mt-1">Showroom stock &amp; sales management</p>
        </div>

        <div className="login-card rounded-2xl border p-6 sm:p-8">
          {                       }
          <div className="login-mode-switch mb-7 grid grid-cols-2 gap-1.5 rounded-xl p-1.5">
            {Object.entries(MODES).map(([key, m]) => (
              <button
                key={key}
                type="button"
                onClick={() => switchMode(key)}
                aria-pressed={mode === key}
                className="login-mode-tab rounded-lg py-2 text-sm font-semibold transition-colors"
              >
                {m.label} Login
              </button>
            ))}
          </div>

          <div className="mb-5">
            <h2 className="login-form-title text-base font-semibold">{copy.heading}</h2>
            <p className="login-form-subtitle mt-1 text-sm">{copy.subtext}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {location.state?.passwordChanged && (
              <div role="status" className="rounded-lg border border-green-100 bg-green-50 px-3 py-2.5 text-sm font-medium text-green-700">
                Password changed. Sign in with your new password.
              </div>
            )}
            {error && (
              <div role="alert" className="login-error rounded-lg border px-3 py-2.5 text-sm font-medium">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="login-username" className="login-label mb-1 block text-sm font-semibold">
                Username
              </label>
              <input
                id="login-username"
                className="login-input w-full rounded-xl border px-3.5 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                placeholder={copy.userPlaceholder}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <div>
              <label htmlFor="login-password" className="login-label mb-1 block text-sm font-semibold">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                className="login-input w-full rounded-xl border px-3.5 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="login-submit w-full rounded-xl bg-brand-500 py-3 text-sm font-semibold text-white transition-colors disabled:opacity-60"
            >
              {loading ? "Signing in..." : `Sign in as ${copy.label}`}
            </button>
          </form>
        </div>

        <p className="login-help mt-6 text-center text-sm">
          Showroom accounts are created by the Admin. Contact your Admin if you don&apos;t have login details.
        </p>
      </div>
      <div className="relative mt-8 w-full">
        <SiteFooter className="login-footer" />
      </div>
    </div>
  );
}
