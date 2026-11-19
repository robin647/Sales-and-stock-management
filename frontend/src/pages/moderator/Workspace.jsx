import { useEffect, useState } from "react";
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { errorMessage } from "../../utils/apiError";
import { Catalog, ProductDetail, ProductTable } from "./Catalog";
import { Downloads, Manage } from "./Manage";
import { Heading, LoadState } from "./components";
import { useWorkspaceData, workspaceApi } from "./data";
import styles from "./workspace.module.css";

function returnPath(location) {
  const target = location.state?.returnTo || new URLSearchParams(location.search).get("next");
  if (target?.startsWith("/moderator/") && !target.includes("\\") && target.length < 2000) {
    const url = new URL(target, window.location.origin);
    if (url.pathname.startsWith("/moderator/") && !/^\/moderator\/login\/?$/.test(url.pathname)) {
      return url.pathname + url.search + url.hash;
    }
  }
  return "/moderator";
}

function StaffLogin({ allowed }) {
  const { loginModerator } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  if (allowed) return <Navigate to={returnPath(location)} replace />;

  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setFailure("");
    try {
      await loginModerator(form.get("username"), form.get("password"));
      navigate(returnPath(location), { replace: true });
    } catch (error) {
      setFailure(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return <main className={styles.login}>
    <form className={styles.panel} onSubmit={submit}>
      <Link to="/">Mahir Sherwani</Link>
      <h1>Moderator workspace</h1>
      <p>Sign in with your staff account.</p>
      <label>Username<input name="username" autoComplete="username" required /></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
      {failure && <p className={styles.error} role="alert">{failure}</p>}
      <button className={styles.primary} disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    </form>
  </main>;
}

function Dashboard() {
  const result = useWorkspaceData("dashboard/");
  return <>
    <Heading title="Overview"><Link className={styles.primary} to="/moderator/products">Browse catalog</Link></Heading>
    <LoadState result={result}>{(data) => <>
      <div className={styles.stats}>
        {[
          ["Products", data.products], ["On offer", data.on_offer], ["Stock units", data.stock],
          ["Out of stock", data.out_of_stock], ["Inactive products", data.inactive], ["Moderators", data.moderators],
        ].filter(([, value]) => value !== undefined).map(([label, value]) => (
          <div className={styles.panel} key={label}><span>{label}</span><strong>{value.toLocaleString()}</strong></div>
        ))}
      </div>
      <section className={styles.panel}><h2>Recently added</h2><ProductTable products={data.recent} /></section>
    </>}</LoadState>
  </>;
}

export default function ModeratorWorkspace() {
  const { user, loading, logout, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [theme, setTheme] = useState(() => localStorage.getItem("moderator-theme") || "light");
  const [notice, setNotice] = useState("");
  const [signingOut, setSigningOut] = useState(false);
  const allowed = isAdmin || user?.role === "moderator";

  useEffect(() => { localStorage.setItem("moderator-theme", theme); }, [theme]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 4500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function signOut() {
    setSigningOut(true);
    try {
      await workspaceApi.post("logout/", null, { timeout: 5000 });
    } catch {
      // Local sign-out still applies if the API is unreachable.
    } finally {
      logout();
      navigate("/moderator/login", { replace: true });
      setSigningOut(false);
    }
  }

  const loginPage = /^\/moderator\/login\/?$/i.test(location.pathname);
  const nav = [
    ["Overview", ""], ["Products", "/products"], ["Asset downloads", "/downloads"],
    ...(isAdmin ? [["Categories", "/categories"], ["Moderator accounts", "/accounts"]] : []),
  ];
  return <div className={styles.workspace} data-theme={theme}>
    {loading ? <p className={styles.state}>Opening workspace…</p> : loginPage ? <StaffLogin allowed={allowed} /> :
      !allowed ? <Navigate to="/moderator/login" state={{ returnTo: location.pathname + location.search + location.hash }} replace /> :
        <div className={styles.shell}>
          <aside className={styles.sidebar}>
            <Link className={styles.brand} to="/moderator"><b>MS</b><span>Mahir Sherwani<small>Moderator workspace</small></span></Link>
            <nav aria-label="Workspace">
              {nav.map(([label, path]) => (
                <NavLink end={!path} key={label} to={"/moderator" + path}
                  className={({ isActive }) => isActive ? styles.active : undefined}>{label}</NavLink>
              ))}
            </nav>
            <div className={styles.profile}>
              <strong>{user.fullName}</strong><small>{isAdmin ? "Administrator" : "Moderator"}</small>
              <button onClick={signOut} disabled={signingOut}>{signingOut ? "Signing out…" : "Sign out"}</button>
            </div>
          </aside>
          <div className={styles.body}>
            <header className={styles.topbar}>
              {isAdmin ? <Link to="/admin/dashboard">Admin dashboard</Link> : <Link to="/">Visit shop</Link>}
              <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "Light theme" : "Dark theme"}</button>
            </header>
            <main className={styles.content}>
              <Routes>
                <Route index element={<Dashboard />} />
                <Route path="products" element={<Catalog isAdmin={isAdmin} notify={setNotice} />} />
                <Route path="products/:id" element={<ProductDetail isAdmin={isAdmin} notify={setNotice} />} />
                <Route path="downloads" element={<Downloads notify={setNotice} />} />
                {isAdmin && <Route path="categories" element={<Manage key="categories" kind="categories" notify={setNotice} />} />}
                {isAdmin && <Route path="accounts" element={<Manage key="accounts" kind="accounts" notify={setNotice} />} />}
                <Route path="*" element={<Navigate to="/moderator" replace />} />
              </Routes>
            </main>
          </div>
        </div>}
    {notice && <div className={styles.toast} role="status">{notice}</div>}
  </div>;
}
