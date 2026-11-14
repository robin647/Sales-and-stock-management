import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { shopApi } from "../../api/endpoints";
import { errorMessage } from "../../utils/apiError";
import "./commerce.css";
const money = value => "৳" + Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 });
const statuses = { pending: "Awaiting verification", confirmed: "Confirmed", shipped: "Shipped", delivered: "Delivered", cancelled: "Cancelled" };
const nextStatuses = { pending: ["pending", "confirmed", "cancelled"], confirmed: ["confirmed", "shipped", "cancelled"], shipped: ["shipped", "delivered"], delivered: ["delivered"], cancelled: ["cancelled"] };
const blankCoupon = { code: "", kind: "percent", value: "", minimum_order: "0", usage_limit: "0", expires_on: "", is_active: true };

export default function CommerceManagement() {
  const [tab, setTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [settings, setSettings] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [coupon, setCoupon] = useState(blankCoupon);
  const [couponId, setCouponId] = useState(null);
  const [summary, setSummary] = useState({ by_status: {} });
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [submittedSearch, setSubmittedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState(false);
  const [selected, setSelected] = useState(null);
  const [update, setUpdate] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  async function loadOrders() {
    setLoading(true); setError("");
    try {
      const [res, stats] = await Promise.all([shopApi.orders({ page, status: filter, search: submittedSearch }), shopApi.summary()]);
      setOrders(res.data.results); setCount(res.data.count); setNext(!!res.data.next); setSummary(stats.data);
    } catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  }
  useEffect(() => { loadOrders(); }, [page, filter, submittedSearch]);
  useEffect(() => { Promise.all([shopApi.settings(), shopApi.coupons()]).then(([s, c]) => { setSettings(s.data); setCoupons(c); }).catch(err => setError(errorMessage(err))); }, []);
  function openOrder(order) {
    setSelected(selected?.id === order.id ? null : order);
    setUpdate({ status: order.status, delivery_payment_status: order.delivery_payment_status, courier: order.courier, tracking_number: order.tracking_number, admin_notes: order.admin_notes });
  }
  async function saveOrder(event) {
    event.preventDefault(); setSaving(true); setError("");
    try { const res = await shopApi.updateOrder(selected.id, update); setSelected(res.data); setNotice("Order updated."); await loadOrders(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function saveSettings(event) {
    event.preventDefault(); setSaving(true); setError("");
    try { const res = await shopApi.updateSettings(settings); setSettings(res.data); setNotice("Store settings saved."); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function saveCoupon(event) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const payload = { ...coupon, expires_on: coupon.expires_on || null };
      if (couponId) await shopApi.updateCoupon(couponId, payload); else await shopApi.createCoupon(payload);
      setCoupons(await shopApi.coupons()); setCoupon(blankCoupon); setCouponId(null); setNotice("Coupon saved.");
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  return <div className="commerce"><div className="commerce-heading"><div><span className="commerce-kicker">COMMERCE DESK</span><h1>Orders & store settings</h1><p>Verify advance delivery payments, fulfil orders and manage promotions.</p></div><Link className="c-button secondary" to="/products">Manage products →</Link></div>
    <div className="commerce-stats">{[["Awaiting verification", summary.by_status.pending || 0], ["To ship", summary.by_status.confirmed || 0], ["Delivered", summary.by_status.delivered || 0], ["Delivered product sales", money(summary.delivered_sales)]].map(([label, value]) => <div className="c-stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
    {error && <div role="alert" className="c-alert error">{error}</div>}{notice && <div role="status" className="c-alert">{notice}<button onClick={() => setNotice("")} aria-label="Dismiss">×</button></div>}
    <div className="commerce-tabs">{[["orders", "Online orders"], ["coupons", "Coupons"], ["settings", "Delivery & payment"]].map(([key, label]) => <button key={key} className={tab === key ? "selected" : ""} onClick={() => setTab(key)}>{label}</button>)}</div>
    {tab === "orders" && <section className="c-panel"><form className="c-toolbar" onSubmit={e => { e.preventDefault(); setPage(1); setSubmittedSearch(search); }}><input aria-label="Search orders" placeholder="Customer name, phone or transaction ID…" value={search} onChange={e => setSearch(e.target.value)} /><button className="c-button secondary">Search</button><select aria-label="Order status" value={filter} onChange={e => { setPage(1); setFilter(e.target.value); }}><option value="">All orders</option>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button type="button" className="c-text-button" onClick={loadOrders}>Refresh</button></form>
      <div className="c-table-wrap"><table className="c-table"><thead><tr><th>Order</th><th>Customer</th><th>Collect on delivery</th><th>Delivery charge</th><th>Status</th><th></th></tr></thead><tbody>{orders.map(order => <tr key={order.id}><td><strong>#{order.id.slice(0, 8).toUpperCase()}</strong><small>{new Date(order.created_at).toLocaleString("en-BD")}</small></td><td>{order.recipient_name}<small>{order.phone} · {order.city}</small></td><td>{money(order.cod_amount)}<small>{order.items.reduce((sum, i) => sum + i.quantity, 0)} items</small></td><td>{money(order.shipping_fee)}<small>{order.delivery_payment_status}</small></td><td><span className="c-badge">{statuses[order.status]}</span></td><td><button className="c-text-button" onClick={() => openOrder(order)}>View order →</button></td></tr>)}</tbody></table></div>{loading && <p className="c-empty">Loading orders…</p>}{!loading && !orders.length && <p className="c-empty">No orders found. Customer checkout orders will appear here.</p>}
      <div className="c-pagination"><button className="c-button secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} · {count} orders</span><button className="c-button secondary" disabled={!next} onClick={() => setPage(page + 1)}>Next</button></div>
      {selected && <div className="c-order-detail"><div className="commerce-heading"><h2>Order #{selected.id.slice(0, 8).toUpperCase()}</h2><button className="c-text-button" onClick={() => setSelected(null)}>Close</button></div><div className="c-order-grid"><div><h3>Customer & delivery</h3><p>{selected.recipient_name}<br />{selected.phone}<br />{selected.address}<br />{selected.city}</p>{selected.notes && <p>Customer note: {selected.notes}</p>}<h3>Items</h3>{selected.items.map(item => <div className="c-summary-line" key={item.id}><span>{item.product_name} {item.size} × {item.quantity}</span><strong>{money(item.line_total)}</strong></div>)}<div className="c-summary-line"><span>Coupon {selected.coupon_code}</span><span>−{money(selected.coupon_discount)}</span></div><div className="c-summary-line total"><span>Product payment on delivery</span><strong>{money(selected.cod_amount)}</strong></div><div className="payment-instructions"><strong>Advance delivery payment: {money(selected.shipping_fee)}</strong><p>Transaction ID: {selected.delivery_payment_reference || "Not required"}</p><p>Verify this transaction in your payment account before confirming. Submitted references do not prove payment.</p>{selected.status === "cancelled" && selected.delivery_payment_status === "verified" && <p>Arrange any delivery charge refund with the customer and record it in the admin notes.</p>}</div></div>
      <form className="c-form" onSubmit={saveOrder}><label>Delivery payment verification<select value={update.delivery_payment_status} onChange={e => setUpdate({ ...update, delivery_payment_status: e.target.value })}>{["submitted", "verified", "rejected", "not_required"].map(s => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></label><label>Order status<select value={update.status} onChange={e => setUpdate({ ...update, status: e.target.value })}>{nextStatuses[selected.status].map(s => <option key={s} value={s}>{statuses[s]}</option>)}</select></label><label>Courier<input maxLength={100} value={update.courier} onChange={e => setUpdate({ ...update, courier: e.target.value })} /></label><label>Tracking number<input maxLength={100} value={update.tracking_number} onChange={e => setUpdate({ ...update, tracking_number: e.target.value })} /></label><label>Private admin notes<textarea rows={3} maxLength={2000} value={update.admin_notes} onChange={e => setUpdate({ ...update, admin_notes: e.target.value })} /></label><p className="c-help">Cancelling a pending or confirmed order returns its reserved items to factory stock. Shipped orders cannot be cancelled here.</p><button className="c-button" disabled={saving}>{saving ? "Saving…" : "Save order"}</button></form></div></div>}
    </section>}
    {tab === "settings" && (settings ? <form className="c-panel c-form c-settings" onSubmit={saveSettings}><h2>Delivery charge paid in advance</h2><p>Product payment is collected on delivery. Customers pay the delivery charge first and submit a transaction ID for your verification.</p><div className="c-form-grid"><label>Delivery charge (৳)<input required type="number" min="0" step="0.01" value={settings.shipping_fee} onChange={e => setSettings({ ...settings, shipping_fee: e.target.value })} /></label><label>Payment method<input required maxLength={60} placeholder="bKash / Nagad" value={settings.payment_method} onChange={e => setSettings({ ...settings, payment_method: e.target.value })} /></label></div><label>Delivery payment number<input required={Number(settings.shipping_fee) > 0} maxLength={30} placeholder="01XXXXXXXXX" value={settings.payment_number} onChange={e => setSettings({ ...settings, payment_number: e.target.value })} /></label><label>Payment instructions<textarea rows={4} placeholder="Send Money / Payment instructions for customers" value={settings.payment_instructions} onChange={e => setSettings({ ...settings, payment_instructions: e.target.value })} /></label><label>WhatsApp number (with country code)<input required pattern="[0-9]{8,20}" value={settings.whatsapp_number} onChange={e => setSettings({ ...settings, whatsapp_number: e.target.value })} /></label><label className="c-checkbox"><input type="checkbox" checked={settings.accepting_orders} onChange={e => setSettings({ ...settings, accepting_orders: e.target.checked })} />Accept online orders</label><button className="c-button" disabled={saving}>{saving ? "Saving…" : "Save store settings"}</button></form> : <p className="c-empty">Loading settings…</p>)}
    {tab === "coupons" && <div className="c-category-layout"><form className="c-panel c-form" onSubmit={saveCoupon}><h2>{couponId ? "Edit coupon" : "Create a coupon"}</h2><label>Coupon code<input required maxLength={30} value={coupon.code} onChange={e => setCoupon({ ...coupon, code: e.target.value.toUpperCase() })} /></label><label>Type<select value={coupon.kind} onChange={e => setCoupon({ ...coupon, kind: e.target.value })}><option value="percent">Percentage off</option><option value="fixed">Fixed taka off</option></select></label><label>Discount value<input required type="number" min="0.01" max={coupon.kind === "percent" ? 100 : undefined} step="0.01" value={coupon.value} onChange={e => setCoupon({ ...coupon, value: e.target.value })} /></label><label>Minimum product subtotal (৳)<input required type="number" min="0" step="0.01" value={coupon.minimum_order} onChange={e => setCoupon({ ...coupon, minimum_order: e.target.value })} /></label><label>Usage limit (0 = unlimited)<input required type="number" min="0" step="1" value={coupon.usage_limit} onChange={e => setCoupon({ ...coupon, usage_limit: e.target.value })} /></label><label>Expiry date · optional<input type="date" value={coupon.expires_on || ""} onChange={e => setCoupon({ ...coupon, expires_on: e.target.value })} /></label><label className="c-checkbox"><input type="checkbox" checked={coupon.is_active} onChange={e => setCoupon({ ...coupon, is_active: e.target.checked })} />Active coupon</label><button className="c-button" disabled={saving}>{saving ? "Saving…" : "Save coupon"}</button>{couponId && <button type="button" className="c-text-button" onClick={() => { setCoupon(blankCoupon); setCouponId(null); }}>Cancel edit</button>}</form><div className="c-category-grid">{coupons.map(c => <article className="c-panel c-category" key={c.id}><span className="c-badge">{c.is_active ? "Active" : "Paused"}</span><h3>{c.code}</h3><p>{c.kind === "percent" ? c.value + "%" : money(c.value)} off products</p><p>Used {c.used_count}{c.usage_limit ? " / " + c.usage_limit : " times"}<br />Minimum {money(c.minimum_order)}<br />{c.expires_on ? "Expires " + c.expires_on : "No expiry"}</p><button className="c-text-button" onClick={() => { setCoupon({ ...c, expires_on: c.expires_on || "" }); setCouponId(c.id); }}>Edit coupon →</button></article>)}</div></div>}
  </div>;
}
