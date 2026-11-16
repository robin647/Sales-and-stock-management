import { useEffect, useState } from "react";
import { Link, NavLink, useParams, useNavigate } from "react-router-dom";
import { ecommerceApi } from "../../api/endpoints";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { errorMessage } from "../../utils/apiError";
import TableActionMenu from "../../components/TableActionMenu";
import Products from "./Products";
import StockAdjustments from "./StockAdjustments";
import CommerceManagement from "./CommerceManagement";
import Customers from "./Customers";
import { ecommerceGroups, ecommerceTitles } from "./ecommerceModules";
import "./ecommerce-admin.css";

const money = value => "৳" + Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 });
const titleCase = text => String(text || "").replaceAll("_", " ");
const defaults = fields => Object.fromEntries(fields.map(field => [field.name, field.default ?? (field.type === "checkbox" ? false : "")]));

function Metric({ title, value, detail, accent }) {
  return <article className={`ec-metric ${accent ? "ec-metric-accent" : ""}`}><span>{title}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function Overview({ report = false }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; ecommerceApi.dashboard().then(res => { if (active) setData(res.data); }).catch(err => { if (active) setError(errorMessage(err)); }); return () => { active = false; }; }, []);
  if (error) return <p role="alert" className="c-alert error">{error}</p>;
  if (!data) return <p className="ec-loading">Loading your store overview…</p>;
  const max = Math.max(1, ...data.trend.map(row => Number(row.sales)));
  function exportReport() {
    const lines = [["Date", "Delivered orders", "Product revenue (BDT)"], ...data.trend.map(row => [row.day, row.count, row.sales])];
    const url = URL.createObjectURL(new Blob([lines.map(row => row.join(",")).join("\n")], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "online-sales-report.csv"; anchor.click(); URL.revokeObjectURL(url);
  }
  return <>
    <div className="ec-welcome"><div><span className="ec-eyebrow">YOUR STORE, AT A GLANCE</span><h2>{report ? "See the story behind your sales." : "A good day to grow your store."}</h2><p>Online sales and operations in one place. Main inventory, showroom and wholesale accounts stay separate.</p></div><Link className="ec-button" to="/admin/ecommerce/products">Manage collection <span>↗</span></Link></div>
    <div className="ec-metrics"><Metric title="Delivered product sales" value={money(data.revenue)} detail="Before returns and operating expenses" accent /><Metric title="Online orders" value={data.orders} detail={`${data.pending} awaiting verification`} /><Metric title="Ready to fulfil" value={data.to_ship} detail="Confirmed orders waiting to ship" /><Metric title="Low-stock products" value={data.low_stock} detail="Dedicated online inventory" /></div>
    <div className="ec-dashboard-grid"><section className="ec-card"><div className="ec-card-heading"><div><span className="ec-eyebrow">SALES PERFORMANCE</span><h3>Delivered product revenue</h3></div><button className="ec-button ec-button-light" onClick={exportReport}>Export CSV ↓</button></div>{data.trend.length ? <div className="ec-chart" role="img" aria-label="Delivered revenue on the latest 30 sale dates">{data.trend.map(row => <div key={row.day} className="ec-chart-column" title={`${row.day}: ${money(row.sales)} · ${row.count} orders`}><span>{money(row.sales)}</span><i style={{ height: `${Math.max(3, Number(row.sales) / max * 160)}px` }} /><small>{new Date(row.day).toLocaleDateString("en-BD", { month: "short", day: "numeric" })}</small></div>)}</div> : <div className="ec-empty">Your sales chart starts with your first delivered order.</div>}<p className="ec-caption">Latest 30 dates with delivered orders. Amounts in BDT; refunds are recorded separately.</p></section>
    <section className="ec-card"><span className="ec-eyebrow">NEEDS YOUR ATTENTION</span><h3>Today’s workspace</h3>{[["orders", data.pending, "Payments to verify"], ["orders", data.to_ship, "Orders to ship"], ["returns", data.returns, "Open return requests"], ["support", data.open_support, "Customer conversations"]].map(([path, count, label]) => <Link key={label} className="ec-attention" to={`/admin/ecommerce/${path}`}><span>{label}</span><b>{count}</b><span>↗</span></Link>)}</section></div>
    {report && data.ledger && <div className="ec-metrics"><Metric title="Recorded online income" value={money(data.ledger.income)} detail="Manual ledger entries" /><Metric title="Recorded online expenses" value={money(data.ledger.expense)} detail="Manual ledger entries" /><Metric title="Ledger balance" value={money(Number(data.ledger.income) - Number(data.ledger.expense))} detail="Not an automatic profit calculation" /><Metric title="Products in collection" value={data.products} detail="Online catalog only" /></div>}
    <div className="ec-dashboard-grid"><section className="ec-card"><div className="ec-card-heading"><h3>Recent orders</h3><Link to="/admin/ecommerce/orders">View all →</Link></div><div className="ec-table-scroll"><table className="ec-table"><thead><tr><th>Order</th><th>Customer</th><th>Total</th><th>Status</th></tr></thead><tbody>{data.recent_orders.map(order => <tr key={order.id}><td>#{order.id.slice(0, 8).toUpperCase()}</td><td>{order.customer}</td><td>{money(order.total)}</td><td><span className="ec-badge">{titleCase(order.status)}</span></td></tr>)}</tbody></table>{!data.recent_orders.length && <p className="ec-empty">New website orders will appear here.</p>}</div></section><section className="ec-card"><div className="ec-card-heading"><h3>Stock watch</h3><Link to="/admin/ecommerce/inventory">Review →</Link></div>{data.stock_alerts.map(row => <div className="ec-attention" key={row.id}><span>{row.name}</span><span className="ec-badge ec-badge-amber">{row.quantity} left</span></div>)}{!data.stock_alerts.length && <p className="ec-empty">No low-stock alerts.</p>}</section></div>
  </>;
}

function Records({ module, schema, audit = false }) {
  const [rows, setRows] = useState([]), [options, setOptions] = useState({});
  const [page, setPage] = useState(1), [next, setNext] = useState(false), [count, setCount] = useState(0);
  const [search, setSearch] = useState(""), [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [editor, setEditor] = useState(false), [editing, setEditing] = useState(null), [form, setForm] = useState({});
  const fields = schema?.fields || [];
  async function load() {
    setLoading(true); setError("");
    try { const response = await ecommerceApi.list(module, { page, search: query }); setRows(response.data.results); setCount(response.data.count); setNext(!!response.data.next); }
    catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [module, page, query]);
  useEffect(() => { if (!audit) ecommerceApi.options(module).then(res => setOptions(res.data)).catch(err => setError(errorMessage(err))); }, [module, audit]);
  useEffect(() => { if (!editor) return; const escape = event => { if (event.key === "Escape" && !busy) setEditor(false); }; document.addEventListener("keydown", escape); return () => document.removeEventListener("keydown", escape); }, [editor, busy]);
  function open(row = null) {
    setEditing(row); setForm(row ? Object.fromEntries(fields.map(field => [field.name, field.type === "password" ? "" : field.type === "datetime-local" && row[field.name] ? new Date(new Date(row[field.name]).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16) : row[field.name] ?? ""])) : defaults(fields)); setError(""); setEditor(true);
  }
  async function save(event) {
    event.preventDefault(); if (busy) return; setBusy(true); setError("");
    const payload = {};
    fields.forEach(field => {
      let value = form[field.name];
      if ((value === "" || value === undefined) && !field.required) { if (field.nullable) payload[field.name] = null; else if (field.allow_blank && field.type !== "password") payload[field.name] = ""; return; }
      if (field.type === "datetime-local" && value) value = new Date(value).toISOString();
      payload[field.name] = value;
    });
    if (editing && module === "team") delete payload.username;
    try { if (editing) await ecommerceApi.update(module, editing.id, payload); else await ecommerceApi.create(module, payload); setEditor(false); setNotice(editing ? "Changes saved." : "Record created."); await load(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  async function remove(row) {
    if (!window.confirm(`Delete ${row.label || "this record"}?`)) return;
    setBusy(true);
    try { await ecommerceApi.remove(module, row.id); setNotice("Record deleted."); await load(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  const columns = audit ? ["created_at", "actor_name", "action", "module", "summary"] : fields.filter(field => !["password", "username"].includes(field.name) && !["textarea"].includes(field.type)).map(field => field.name).slice(0, 6);
  function display(row, key) {
    const field = fields.find(field => field.name === key), value = row[key];
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (key === "created_at") return new Date(value).toLocaleString("en-BD");
    if (field?.type === "relation") return options[key]?.find(item => String(item.value) === String(value))?.label || `#${String(value).slice(0, 8)}`;
    if (field?.type === "select") return field.options.find(item => item.value === value)?.label || value;
    if (field?.type === "decimal" && !["exchange_rate", "commission_percent"].includes(key)) return money(value);
    return String(value);
  }
  return <section className="ec-card ec-records"><div className="ec-card-heading"><div><span className="ec-eyebrow">{audit ? "READ-ONLY EVENT HISTORY" : `${count} RECORDS`}</span><h2>{audit ? "Security & Activity Logs" : schema?.title}</h2><p>{audit ? "Successful and denied ecommerce API changes. Passwords, tokens and request bodies are never logged." : schema?.description}</p></div>{schema?.can_write && <button className="ec-button" onClick={() => open()}>+ Add record</button>}</div>
    {error && !editor && <p role="alert" className="c-alert error">{error}</p>}{notice && <p role="status" className="c-alert">{notice}</p>}
    <form className="ec-toolbar" onSubmit={event => { event.preventDefault(); setPage(1); setQuery(search); }}><input aria-label="Search records" placeholder="Search records…" value={search} onChange={event => setSearch(event.target.value)} /><button className="ec-button ec-button-light">Search</button><button type="button" className="ec-button ec-button-light" onClick={load}>Refresh ↻</button></form>
    <div className="ec-table-scroll"><table className="ec-table"><thead><tr>{columns.map(key => <th key={key}>{fields.find(field => field.name === key)?.label || titleCase(key)}</th>)}{!audit && <th>Actions</th>}</tr></thead><tbody>{rows.map(row => <tr key={row.id}>{columns.map(key => <td key={key}>{["status", "access_role", "kind"].includes(key) ? <span className="ec-badge">{display(row, key)}</span> : display(row, key)}</td>)}{!audit && <td><TableActionMenu><button type="button" onClick={() => open(row)}>{schema.can_write ? "View / update" : "View details"}</button>{schema.can_write && schema.can_delete && <button type="button" disabled={busy} className="text-red-700" onClick={() => remove(row)}>Delete</button>}</TableActionMenu></td>}</tr>)}</tbody></table></div>
    {loading ? <p className="ec-loading">Loading records…</p> : !rows.length && <div className="ec-empty"><span className="ec-empty-icon">◇</span><h3>{query ? "No matching records" : "A clear start"}</h3><p>{query ? "Try another search." : "Your records will appear here as you run your store."}</p>{schema?.can_write && <button className="ec-button" onClick={() => open()}>Create the first record</button>}</div>}
    <div className="ec-pagination"><span>{count} records · Page {page}</span><div><button disabled={page === 1 || loading} onClick={() => setPage(value => value - 1)}>← Previous</button><button disabled={!next || loading} onClick={() => setPage(value => value + 1)}>Next →</button></div></div>
    {editor && <div className="ec-drawer-backdrop"><section className="ec-drawer" role="dialog" aria-modal="true" aria-labelledby="ec-editor-title"><header><div><span className="ec-eyebrow">{schema.title}</span><h2 id="ec-editor-title">{editing ? "Record details" : "Create a record"}</h2></div><button aria-label="Close editor" disabled={busy} onClick={() => setEditor(false)}>×</button></header><form onSubmit={save}>{error && <p role="alert" className="c-alert error">{error}</p>}<div className="ec-fields">{fields.map((field, index) => <label className={field.type === "textarea" ? "ec-field-wide" : ""} key={field.name}>{field.label}{field.required && " *"}{field.type === "textarea" ? <textarea disabled={!schema.can_write || busy} rows={4} maxLength={field.maxLength} required={field.required} value={form[field.name] ?? ""} onChange={event => setForm({ ...form, [field.name]: event.target.value })} /> : ["select", "relation"].includes(field.type) ? <select disabled={!schema.can_write || busy} required={field.required} value={form[field.name] ?? ""} onChange={event => setForm({ ...form, [field.name]: event.target.value })}><option value="">Choose…</option>{(field.options || options[field.name] || []).map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select> : <input autoFocus={index === 0} disabled={!schema.can_write || busy || editing && field.name === "username"} type={field.type === "decimal" ? "number" : field.type} min={field.min} max={field.max} step={field.type === "decimal" ? "any" : field.type === "number" ? "1" : undefined} maxLength={field.maxLength} checked={field.type === "checkbox" ? !!form[field.name] : undefined} required={field.required && !(editing && field.type === "password")} value={field.type === "checkbox" ? undefined : form[field.name] ?? ""} onChange={event => setForm({ ...form, [field.name]: field.type === "checkbox" ? event.target.checked : event.target.value })} />}{field.help && <small>{field.help}</small>}</label>)}</div><footer><button type="button" className="ec-button ec-button-light" disabled={busy} onClick={() => setEditor(false)}>Close</button>{schema.can_write && <button className="ec-button" disabled={busy}>{busy ? "Saving…" : "Save record"}</button>}</footer></form></section></div>}
  </section>;
}

function StoreSettings() {
  const [form, setForm] = useState(null), [error, setError] = useState(""), [notice, setNotice] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { ecommerceApi.preferences().then(res => setForm(res.data)).catch(err => setError(errorMessage(err))); }, []);
  async function save(event) { event.preventDefault(); setBusy(true); try { await ecommerceApi.savePreferences(form); setNotice("Store settings saved."); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); } }
  return <><section className="ec-card"><span className="ec-eyebrow">YOUR STORE IDENTITY</span><h2>Settings</h2>{error && <p className="c-alert error">{error}</p>}{notice && <p role="status" className="c-alert">{notice}</p>}{form && <form onSubmit={save}><div className="ec-fields">{["store_name", "support_email", "support_phone", "address", "low_stock_threshold", "announcement", "return_policy", "privacy_policy"].map(key => <label key={key}>{titleCase(key)}{key.endsWith("policy") || key === "address" ? <textarea rows={4} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} /> : <input required={key === "store_name"} type={key === "low_stock_threshold" ? "number" : key === "support_email" ? "email" : "text"} min="0" value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} />}</label>)}</div><button className="ec-button" disabled={busy}>{busy ? "Saving…" : "Save settings"}</button></form>}</section><CommerceManagement embedded initialTab="settings" /></>;
}

export default function EcommerceAdmin() {
  const { module = "dashboard" } = useParams();
  const { user, logout } = useAuth(); const { toggleTheme } = useTheme(); const navigate = useNavigate();
  const [workspace, setWorkspace] = useState(null), [error, setError] = useState(""), [mobileOpen, setMobileOpen] = useState(false), [navSearch, setNavSearch] = useState("");
  useEffect(() => { ecommerceApi.workspace().then(res => setWorkspace(res.data)).catch(err => setError(errorMessage(err))); }, []);
  const permission = module === "categories" ? "products" : module;
  const allowed = workspace?.access.includes(permission);
  let content;
  if (!workspace) content = <p className="ec-loading">{error || "Preparing your ecommerce workspace…"}</p>;
  else if (!allowed) content = <div className="ec-card ec-empty"><h2>Access restricted</h2><p>Your ecommerce role does not include this module.</p><Link to="/admin/ecommerce/dashboard">Back to dashboard</Link></div>;
  else if (module === "dashboard" || module === "reports") content = <Overview key={module} report={module === "reports"} />;
  else if (module === "products" || module === "categories") content = <><Products readOnly={!workspace.write_access.includes("products")} key={module} online initialTab={module === "categories" ? "categories" : "products"} />{module === "categories" && workspace.modules.brands && <Records key="brands" module="brands" schema={workspace.modules.brands} />}</>;
  else if (module === "inventory") content = <StockAdjustments online readOnly={!workspace.write_access.includes("inventory")} />;
  else if (module === "orders") content = <CommerceManagement readOnly={!workspace.write_access.includes("orders")} embedded key="orders" initialTab="orders" />;
  else if (module === "customers") content = <Customers />;
  else if (module === "settings") content = <StoreSettings />;
  else if (module === "audit") content = <Records module="audit" audit />;
  else if (workspace.modules[module]) content = <><Records key={module} module={module} schema={workspace.modules[module]} />{module === "purchases" && workspace.modules.suppliers && <Records key="suppliers" module="suppliers" schema={workspace.modules.suppliers} />}{module === "campaigns" && <CommerceManagement embedded key="coupons" initialTab="coupons" />}</>;
  else content = <div className="ec-card ec-empty">Choose a module from the menu.</div>;
  return <div className="ec-app commerce">{mobileOpen && <button className="ec-mobile-shade" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}<aside className={`ec-sidebar ${mobileOpen ? "ec-sidebar-open" : ""}`}><Link to="/admin/ecommerce/dashboard" className="ec-brand"><span>M</span><div>MAHIR<small>ECOMMERCE ADMIN</small></div></Link><div className="ec-workspace-label"><i /> Online store workspace</div><input className="ec-nav-search" aria-label="Find admin module" placeholder="Find a module…" value={navSearch} onChange={event => setNavSearch(event.target.value)} /><nav>{ecommerceGroups.map(group => { const items = group.items.filter(([id, title]) => (!workspace || workspace.access.includes(id === "categories" ? "products" : id)) && title.toLowerCase().includes(navSearch.toLowerCase())); return items.length ? <div className="ec-nav-group" key={group.title}><span>{group.title}</span>{items.map(([id, title, icon]) => <NavLink key={id} to={`/admin/ecommerce/${id}`} onClick={() => setMobileOpen(false)}><i aria-hidden="true">{icon}</i>{title}</NavLink>)}</div> : null; })}</nav><div className="ec-sidebar-bottom"><Link to="/shop">View storefront ↗</Link>{user?.role === "admin" && <Link to="/admin/dashboard">Showroom & wholesale →</Link>}<button onClick={() => { logout(); navigate("/admin/login"); }}>Sign out</button></div></aside><div className="ec-main"><header className="ec-topbar"><div><button className="ec-menu-toggle" onClick={() => setMobileOpen(value => !value)} aria-label="Toggle navigation">☰</button><span>Workspace <b>/</b> {ecommerceTitles[module] || "Ecommerce"}</span></div><div><button onClick={toggleTheme} aria-label="Toggle colour theme">◐</button><span className="ec-avatar">{(user?.fullName || "A").charAt(0)}</span><div className="ec-user"><strong>{user?.fullName}</strong><small>{titleCase(workspace?.role || "Administrator")}</small></div></div></header><main className="ec-main-content"><div className="ec-page-heading"><span className="ec-eyebrow">ECOMMERCE ADMIN</span><h1>{ecommerceTitles[module] || "Workspace"}</h1></div>{content}<footer className="ec-footnote">MAHIR SHERWANI · Online commerce workspace</footer></main></div></div>;
}
