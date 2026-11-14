import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { productApi, shopApi } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../utils/apiError";
import "./admin/commerce.css";
const money = value => "৳" + Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 });
const labels = { pending: "Awaiting delivery payment verification", confirmed: "Order confirmed", shipped: "On the way", delivered: "Delivered", cancelled: "Cancelled" };
function readBag() { try { const value = JSON.parse(localStorage.getItem("mahir-shopping-bag") || "{}"); return value && typeof value === "object" && !Array.isArray(value) ? value : {}; } catch { return {}; } }
function requestKey() {
  let key = sessionStorage.getItem("mahir-checkout-key");
  if (!key) { key = crypto.randomUUID(); sessionStorage.setItem("mahir-checkout-key", key); }
  return key;
}
export default function ShopAccount() {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const isCheckout = location.pathname === "/checkout";
  const [bag] = useState(readBag);
  const [products, setProducts] = useState([]);
  const [settings, setSettings] = useState(null);
  const [quote, setQuote] = useState(null);
  const [coupon, setCoupon] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState("");
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState({ recipient_name: "", phone: "", address: "", city: "", notes: "", delivery_payment_reference: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(null);
  const [page, setPage] = useState(1);
  const [next, setNext] = useState(false);
  const [couponBusy, setCouponBusy] = useState(false);
  const items = Object.entries(bag).filter(([id, qty]) => Number.isInteger(Number(id)) && Number.isInteger(qty) && qty > 0).map(([id, quantity]) => ({ product: Number(id), quantity }));
  async function loadOrders() {
    const res = await shopApi.orders({ page }); setOrders(res.data.results); setNext(!!res.data.next);
  }
  useEffect(() => {
    if (user?.role !== "customer") { setLoading(false); return; }
    let active = true;
    setLoading(true); setError("");
    const work = isCheckout ? Promise.all([productApi.listAll({ is_active: true, storefront: true }), shopApi.settings(), items.length ? shopApi.quote({ items }) : Promise.resolve(null)]).then(([p, s, q]) => { if (active) { setProducts(p); setSettings(s.data); setQuote(q?.data || null); } }) : shopApi.orders({ page }).then(res => { if (active) { setOrders(res.data.results); setNext(!!res.data.next); } });
    work.catch(err => { if (active) setError(errorMessage(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user?.id, isCheckout, page]);
  async function applyCoupon() {
    setCouponBusy(true); setError("");
    try { const res = await shopApi.quote({ items, coupon }); setQuote(res.data); setAppliedCoupon(coupon.trim().toUpperCase()); }
    catch (err) { setError(errorMessage(err)); }
    finally { setCouponBusy(false); }
  }
  async function submitOrder(event) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const res = await shopApi.placeOrder({ ...form, items, coupon: appliedCoupon, expected_total: quote.total, expected_shipping_fee: quote.shipping_fee, request_key: requestKey() });
      setSuccess(res.data); localStorage.setItem("mahir-shopping-bag", "{}"); sessionStorage.removeItem("mahir-checkout-key"); sessionStorage.removeItem("mahir-resume-order");
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  async function cancelOrder(order) {
    if (!window.confirm("Cancel this order? If you already paid the delivery charge, contact the shop about a refund.")) return;
    setError(""); setSaving(true);
    try { await shopApi.cancelOrder(order.id); await loadOrders(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  const selectedProducts = products.filter(p => bag[p.id]);
  return <div className="commerce shop-customer-page"><header className="shop-customer-header"><Link to="/shop"><strong>MAHIR SHERWANI</strong></Link><div className="commerce-actions"><Link to="/shop">Continue shopping</Link><Link to="/my-orders">My orders</Link></div></header>
    <span className="commerce-kicker">{isCheckout ? "YOUR NEXT SPECIAL MOMENT" : "YOUR MAHIR ACCOUNT"}</span><h1>{isCheckout ? "Checkout" : "My orders"}</h1>
    {error && <div className="c-alert error" role="alert">{error}</div>}
    {authLoading ? <p className="c-empty">Loading your account…</p> : user?.role !== "customer" ? <div className="c-panel c-empty"><h2>Sign in to your customer account</h2><p>Your shopping bag is saved.</p><div className="commerce-actions" style={{ justifyContent: "center" }}><Link className="c-button" to="/login" state={{ customerCreated: true, returnToOrder: true, returnTo: location.pathname }}>Customer sign in</Link><Link className="c-button secondary" to="/signup" state={{ returnTo: location.pathname }}>Create an account</Link></div></div> : loading ? <p className="c-empty">Loading…</p> : success && isCheckout ? <div className="c-panel c-empty"><span className="c-badge">Order received</span><h2>Thank you, {success.recipient_name}.</h2><p>Order #{success.id.slice(0, 8).toUpperCase()}<br />We will verify your delivery charge payment before confirming your order.</p><p>Pay <strong>{money(success.cod_amount)}</strong> for the products on delivery.</p><Link className="c-button" to="/my-orders">Track your order →</Link></div> : isCheckout ? !items.length ? <div className="c-panel c-empty"><h2>Your bag is empty</h2><Link className="c-button" to="/shop">Explore the collection</Link></div> : <div className="checkout-layout"><form className="c-panel c-form" onSubmit={submitOrder}><h2>Delivery details</h2><div className="c-form-grid"><label>Full name<input required autoComplete="name" maxLength={120} value={form.recipient_name} onChange={e => setForm({ ...form, recipient_name: e.target.value })} /></label><label>Mobile number<input required type="tel" autoComplete="tel" maxLength={25} value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></label></div><label>Street address<textarea required autoComplete="street-address" maxLength={1000} rows={3} placeholder="House, road, area and delivery instructions" value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} /></label><label>City / district<input required autoComplete="address-level2" maxLength={100} value={form.city} onChange={e => setForm({ ...form, city: e.target.value })} /></label><label>Order note · optional<textarea rows={2} maxLength={1000} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></label>
      {settings && Number(quote?.shipping_fee) > 0 && <div className="payment-instructions"><h3>1. Pay delivery charge in advance</h3><p>Send <strong>{money(quote.shipping_fee)}</strong> via <strong>{settings.payment_method}</strong> to:</p><h2>{settings.payment_number || "Payment number not configured"}</h2><p>{settings.payment_instructions}</p><label>Delivery payment transaction ID<input required maxLength={100} autoComplete="off" value={form.delivery_payment_reference} onChange={e => setForm({ ...form, delivery_payment_reference: e.target.value })} placeholder="Enter the transaction ID after payment" /></label><p>Only the delivery charge is paid now. Your payment will be verified by the shop.</p></div>}<h3>2. Pay product price on delivery</h3><p>Product amount to collect: <strong>{money(quote?.cod_amount)}</strong></p><button className="c-button" disabled={saving || !quote || !settings?.accepting_orders || (Number(quote.shipping_fee) > 0 && !settings?.payment_number)}>{saving ? "Placing your order…" : "Place order · Cash on Delivery"}</button>{settings && !settings.accepting_orders && <p>Online orders are temporarily paused.</p>}</form>
      <aside className="c-panel checkout-summary"><h2>Order summary</h2>{selectedProducts.map(p => <div className="checkout-item" key={p.id}>{p.image && <img src={p.image} alt="" />}<div><strong>{p.name}</strong><small>{p.size} × {bag[p.id]}</small></div><strong>{money(Number(p.effective_price ?? p.discount_price ?? p.selling_price) * bag[p.id])}</strong></div>)}<div className="c-toolbar" style={{ padding: "16px 0" }}><input aria-label="Coupon code" placeholder="Coupon code" value={coupon} onChange={e => setCoupon(e.target.value)} /><button className="c-button secondary" disabled={couponBusy} onClick={applyCoupon}>{couponBusy ? "Checking…" : "Apply"}</button></div>{appliedCoupon && <p>Applied: {appliedCoupon}</p>}{quote && <><div className="c-summary-line"><span>Products</span><span>{money(quote.subtotal)}</span></div><div className="c-summary-line"><span>Coupon savings</span><span>−{money(quote.coupon_discount)}</span></div><div className="c-summary-line"><span>Delivery · pay in advance</span><span>{money(quote.shipping_fee)}</span></div><div className="c-summary-line total"><span>Total</span><strong>{money(quote.total)}</strong></div><div className="c-summary-line"><span>Pay on delivery</span><strong>{money(quote.cod_amount)}</strong></div></>}<p className="c-help">Prices and stock are checked again when you place the order.</p></aside></div> : <>{orders.map(order => <article className="c-panel c-order-card" key={order.id}><header><div><strong>#{order.id.slice(0, 8).toUpperCase()}</strong><p>{new Date(order.created_at).toLocaleDateString("en-BD")}</p></div><span className="c-badge">{labels[order.status]}</span></header>{order.items.map(item => <div className="c-summary-line" key={item.id}><span>{item.product_name} {item.size} × {item.quantity}</span><strong>{money(item.line_total)}</strong></div>)}<div className="c-summary-line"><span>Delivery charge · {order.delivery_payment_status}</span><span>{money(order.shipping_fee)}</span></div><div className="c-summary-line total"><span>Product amount on delivery</span><strong>{money(order.cod_amount)}</strong></div>{order.coupon_code && <p>Coupon {order.coupon_code}: −{money(order.coupon_discount)}</p>}<p>Deliver to: {order.recipient_name}, {order.address}, {order.city}</p>{order.tracking_number && <p>Courier: {order.courier} · Tracking: <strong>{order.tracking_number}</strong></p>}{order.status === "cancelled" && order.delivery_payment_status === "verified" && <p>For a delivery charge refund, please contact the shop with your order number.</p>}{order.status === "pending" && <button disabled={saving} className="c-text-button" onClick={() => cancelOrder(order)}>Cancel pending order</button>}</article>)}{!orders.length && <div className="c-panel c-empty"><h2>No orders yet</h2><p>Your orders and delivery updates will appear here.</p><Link className="c-button" to="/shop">Find your next favourite</Link></div>}<div className="c-pagination"><button className="c-button secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button className="c-button secondary" disabled={!next} onClick={() => setPage(page + 1)}>Next</button></div></>}
  </div>;
}
