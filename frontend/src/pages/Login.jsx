import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { SiteFooter } from "../components/SiteFooter";
import { errorMessage } from "../utils/apiError";

const copy = {
  customer: { title: "Customer sign in", description: "Sign in with your verified email and password.", label: "Email address", type: "email" },
  admin: { title: "Admin sign in", description: "Administration and ecommerce team workspace.", label: "Admin / team username", type: "text" },
  showroom: { title: "Showroom sign in", description: "Use the showroom login created by your administrator.", label: "Showroom username", type: "text" },
};
export default function Login({ portal = "customer" }) {
  const location = useLocation(), navigate = useNavigate();
  const { login, loginShowroom, loginCustomer, logout } = useAuth();
  const [username, setUsername] = useState(location.state?.email || ""), [password, setPassword] = useState("");
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { setUsername(location.state?.email || ""); setPassword(""); setError(""); }, [portal, location.state?.email]);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const user = portal === "customer" ? await loginCustomer(username, password) : portal === "showroom" ? await loginShowroom(username, password) : await login(username, password);
      const allowed = portal === "customer" ? user?.role === "customer" : portal === "showroom" ? user?.role === "showroom_user" : ["admin", "ecommerce_staff"].includes(user?.role);
      if (!allowed) { logout(); setError("This account belongs to a different login portal."); return; }
      const target = location.state?.returnTo || "";
      const safeTarget = portal === "admin" ? (user.role === "admin" ? target.startsWith("/admin/") : target.startsWith("/admin/ecommerce/")) && target !== "/admin/login" : portal === "showroom" ? target.startsWith("/showroom/") && target !== "/showroom/login" : ["/checkout", "/my-orders", "/support"].includes(target);
      navigate(safeTarget ? target : portal === "customer" ? "/" : portal === "showroom" ? "/showroom/dashboard" : user.role === "ecommerce_staff" ? "/admin/ecommerce/dashboard" : "/admin/dashboard", { replace: true });
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  const mode = copy[portal];
  return <div className="login-page flex min-h-screen flex-col items-center justify-center px-4 py-10"><div className="w-full max-w-md"><Link to="/" className="login-brand mb-7 block text-center"><span className="login-brandmark mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-lg font-bold text-white">MS</span><span className="login-title block text-2xl font-bold">Mahir Sherwani</span><span className="login-subtitle mt-2 block text-sm">{portal === "customer" ? "Your next occasion starts here." : portal === "admin" ? "Administration workspace" : "Showroom workspace"}</span></Link><section className="login-card rounded-2xl border p-6 sm:p-8"><h1 className="login-form-title text-xl font-semibold">{mode.title}</h1><p className="login-form-subtitle mb-6 mt-2 text-sm">{mode.description}</p>{(location.state?.customerCreated || location.state?.emailVerified) && portal === "customer" && <p role="status" className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-800">Email verified. Sign in with your email and password.</p>}{location.state?.passwordChanged && <p role="status" className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-800">Password changed. Sign in again.</p>}{error && <p role="alert" className="login-error mb-4 rounded-lg border p-3 text-sm">{error}</p>}<form onSubmit={submit} className="space-y-4"><label className="login-label block text-sm font-semibold">{mode.label}<input required type={mode.type} autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} className="login-input mt-2 w-full rounded-xl border px-3.5 py-3 text-sm" /></label><label className="login-label block text-sm font-semibold">Password<input required type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} className="login-input mt-2 w-full rounded-xl border px-3.5 py-3 text-sm" /></label><button disabled={busy} className="login-submit w-full rounded-xl py-3 text-sm font-semibold">{busy ? "Signing in..." : "Sign in"}</button></form>{portal === "customer" && <div className="mt-5 space-y-3 text-sm"><p>New here? <Link to="/signup" className="text-brand-700">Create your account</Link></p><p><Link to="/verify-email" state={{ email: username }} className="text-brand-700">Verify an existing customer email</Link></p></div>}{portal === "showroom" && <p className="login-help mt-5 text-sm">Your administrator manages your showroom login. Contact them if you need help.</p>}</section></div><div className="mt-8 w-full"><SiteFooter className="login-footer" /></div></div>;
}
