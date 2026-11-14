import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { customerApi } from "../../api/endpoints";
import { errorMessage } from "../../utils/apiError";
import "./commerce.css";

const money = value => "৳" + Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 });
const date = value => value ? new Date(value).toLocaleString("en-BD") : "Not recorded";
const statusLabels = { pending: "Awaiting verification", confirmed: "Confirmed", shipped: "Shipped", delivered: "Delivered", cancelled: "Cancelled" };

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [summary, setSummary] = useState({ total: 0, active: 0, inactive: 0, with_orders: 0 });
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [hasOrders, setHasOrders] = useState(false);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [orders, setOrders] = useState([]);
  const [orderPage, setOrderPage] = useState(1);
  const [orderCount, setOrderCount] = useState(0);
  const [orderNext, setOrderNext] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [confirmation, setConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    Promise.all([customerApi.list({ page, search, status: filter, has_orders: hasOrders ? "true" : "" }), customerApi.summary()])
      .then(([list, stats]) => { if (active) { setCustomers(list.data.results); setCount(list.data.count); setHasNext(!!list.data.next); setSummary(stats.data); } })
      .catch(err => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, search, filter, hasOrders, attempt]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setDetailLoading(true); setDetailError("");
    Promise.all([customerApi.get(selectedId), customerApi.orders(selectedId, { page: orderPage })])
      .then(([profile, history]) => { if (active) { setSelected(profile.data); setOrders(history.data.results); setOrderCount(history.data.count); setOrderNext(!!history.data.next); } })
      .catch(err => { if (active) setDetailError(errorMessage(err)); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedId, orderPage, attempt]);

  function viewCustomer(customer) {
    setSelected(null); setOrders([]); setOrderPage(1); setSelectedId(customer.id);
  }
  function confirmDelete(customer) {
    setDeleteTarget(customer); setConfirmation(""); setDeleteError("");
  }
  async function deleteCustomer(event) {
    event.preventDefault();
    if (confirmation !== "DELETE" || deleting) return;
    setDeleting(true); setDeleteError("");
    try {
      const response = await customerApi.delete(deleteTarget.id);
      setNotice(response.data.detail); setDeleteTarget(null);
      if (selectedId === deleteTarget.id) { setSelectedId(null); setSelected(null); }
      if (customers.length === 1 && page > 1) setPage(value => value - 1);
      setAttempt(value => value + 1);
    } catch (err) { setDeleteError(errorMessage(err)); }
    finally { setDeleting(false); }
  }

  return <div className="commerce">
    <div className="commerce-heading"><div><span className="commerce-kicker">CUSTOMER DIRECTORY</span><h1>Customers</h1><p>Account details, contact information and the complete order history in one place.</p></div><Link to="/online-orders" className="c-button secondary">Manage online orders →</Link></div>
    <div className="commerce-stats">{[["Total customers", summary.total], ["Active accounts", summary.active], ["Inactive accounts", summary.inactive], ["Customers with orders", summary.with_orders]].map(([label, value]) => <div className="c-stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
    {error && <div role="alert" className="c-alert error">{error}</div>}{notice && <div className="c-alert" role="status">{notice}<button onClick={() => setNotice("")} aria-label="Dismiss notification">×</button></div>}
    <section className="c-panel"><form className="c-toolbar" onSubmit={event => { event.preventDefault(); setPage(1); setSearch(query); setAttempt(value => value + 1); }}><input aria-label="Search customers" placeholder="Search name, email or phone…" value={query} onChange={event => setQuery(event.target.value)} /><button className="c-button secondary">Search</button><select aria-label="Account status" value={filter} onChange={event => { setFilter(event.target.value); setPage(1); }}><option value="">All accounts</option><option value="active">Active</option><option value="inactive">Inactive</option></select><label className="customer-order-filter"><input type="checkbox" checked={hasOrders} onChange={event => { setHasOrders(event.target.checked); setPage(1); }} />Has orders</label><button type="button" className="c-text-button" onClick={() => setAttempt(value => value + 1)}>Refresh</button></form>
      <div className="c-table-wrap"><table className="c-table"><thead><tr><th>Customer</th><th>Contact</th><th>Orders</th><th>Delivered product spend</th><th>Account</th><th>Actions</th></tr></thead><tbody>{!loading && customers.map(customer => <tr key={customer.id}><td><div className="c-product-cell"><span className="customer-avatar">{customer.name.charAt(0).toUpperCase()}</span><div><strong>{customer.name}</strong><small>Customer #{customer.id}</small></div></div></td><td>{customer.email ? <a href={"mailto:" + customer.email}>{customer.email}</a> : "No email"}<small>{customer.phone_number ? <a href={"tel:" + customer.phone_number}>{customer.phone_number}</a> : customer.username}</small></td><td><strong>{customer.order_count}</strong><small>{customer.active_order_count} ongoing · {customer.delivered_count} delivered</small></td><td>{money(customer.delivered_spend)}</td><td><span className={customer.is_active ? "c-badge" : "c-badge muted"}>{customer.is_active ? "Active" : "Inactive"}</span><small>Joined {new Date(customer.date_joined).toLocaleDateString("en-BD")}</small></td><td><div className="commerce-actions"><button className="c-text-button" onClick={() => viewCustomer(customer)}>View details</button><button className="c-text-button customer-delete-button" onClick={() => confirmDelete(customer)}>Delete account</button></div></td></tr>)}</tbody></table></div>
      {loading && <p className="c-empty" role="status">Loading customers…</p>}{!loading && !customers.length && <div className="c-empty"><h3>No customers found</h3><p>Customer signups will appear here. Try another search or filter.</p></div>}<div className="c-pagination"><button className="c-button secondary" disabled={page === 1 || loading} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {page} · {count} customers</span><button className="c-button secondary" disabled={!hasNext || loading} onClick={() => setPage(value => value + 1)}>Next</button></div>
    </section>
    {selectedId && !deleteTarget && <div className="c-modal-backdrop" onClick={event => { if (event.target === event.currentTarget) setSelectedId(null); }}><section className="c-modal customer-details-modal" role="dialog" aria-modal="true" aria-labelledby="customer-details-title" onKeyDown={event => { if (event.key === "Escape") setSelectedId(null); }}><div className="c-modal-heading"><div><span className="commerce-kicker">CUSTOMER PROFILE</span><h2 id="customer-details-title">{selected?.name || "Customer details"}</h2></div><button autoFocus aria-label="Close customer details" onClick={() => setSelectedId(null)}>×</button></div><div className="c-form">{detailError && <div role="alert" className="c-alert error">{detailError}</div>}{detailLoading ? <p className="c-empty">Loading profile & orders…</p> : selected && <><div className="customer-profile-grid"><div><h3>Contact information</h3><dl className="customer-facts"><dt>Full name</dt><dd>{selected.name}</dd><dt>Email</dt><dd>{selected.email ? <a href={"mailto:" + selected.email}>{selected.email}</a> : "Not provided"}</dd><dt>Phone</dt><dd>{selected.phone_number ? <a href={"tel:" + selected.phone_number}>{selected.phone_number}</a> : "Not provided"}</dd><dt>Username</dt><dd>{selected.username}</dd><dt>Customer ID</dt><dd>#{selected.id}</dd></dl></div><div><h3>Account information</h3><dl className="customer-facts"><dt>Status</dt><dd><span className={selected.is_active ? "c-badge" : "c-badge muted"}>{selected.is_active ? "Active" : "Inactive"}</span></dd><dt>Joined</dt><dd>{date(selected.date_joined)}</dd><dt>Last login</dt><dd>{date(selected.last_login)}</dd><dt>Latest order</dt><dd>{date(selected.last_order_at)}</dd></dl><p className="c-help">Delivery addresses are recorded on each order. Last login is shown when it has been recorded.</p></div></div><div className="commerce-stats customer-profile-stats">{[["Orders", selected.order_count], ["Ongoing", selected.active_order_count], ["Delivered", selected.delivered_count], ["Delivered product spend", money(selected.delivered_spend)]].map(([label, value]) => <div className="c-stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><h2>Order history <small>({orderCount})</small></h2>{orders.length ? orders.map(order => <details key={order.id} className="customer-order" open={orders.length === 1}><summary><span><strong>#{order.id.slice(0, 8).toUpperCase()}</strong><small>{date(order.created_at)}</small></span><span className="c-badge">{statusLabels[order.status]}</span><strong>{money(order.total)}</strong></summary><div className="customer-order-body"><div className="c-order-grid"><div><h3>Delivery details</h3><p>{order.recipient_name}<br />{order.phone}<br />{order.address}<br />{order.city}</p><p>Courier: {order.courier || "Not assigned"}<br />Tracking: {order.tracking_number || "Not assigned"}</p>{order.notes && <p>Customer note: {order.notes}</p>}{order.admin_notes && <p>Private admin note: {order.admin_notes}</p>}</div><div><h3>Payment details</h3><div className="c-summary-line"><span>Product subtotal</span><strong>{money(order.subtotal)}</strong></div><div className="c-summary-line"><span>Coupon {order.coupon_code}</span><span>−{money(order.coupon_discount)}</span></div><div className="c-summary-line"><span>Advance delivery charge</span><span>{money(order.shipping_fee)}</span></div><p>Transaction ID: <strong>{order.delivery_payment_reference || "Not required"}</strong><br />Verification: {order.delivery_payment_status}</p><div className="c-summary-line total"><span>Product amount · COD</span><strong>{money(order.cod_amount)}</strong></div></div></div><div className="c-table-wrap"><table className="c-table"><thead><tr><th>Product</th><th>Code / size</th><th>Quantity</th><th>Unit price</th><th>Total</th></tr></thead><tbody>{order.items.map(item => <tr key={item.id}><td>{item.product_name}</td><td>{item.code || "—"}<small>{item.size || "Standard"}</small></td><td>{item.quantity}</td><td>{money(item.unit_price)}</td><td>{money(item.line_total)}</td></tr>)}</tbody></table></div></div></details>) : <p className="c-empty">This customer has not placed an online order yet.</p>}<div className="c-pagination"><button className="c-button secondary" disabled={orderPage === 1} onClick={() => setOrderPage(value => value - 1)}>Previous orders</button><span>Page {orderPage}</span><button className="c-button secondary" disabled={!orderNext} onClick={() => setOrderPage(value => value + 1)}>Next orders</button></div><div className="c-modal-footer"><button className="c-button customer-danger" onClick={() => confirmDelete(selected)}>Delete customer account</button></div></>}</div></section></div>}
    {deleteTarget && <div className="c-modal-backdrop"><section className="c-modal customer-delete-modal" role="dialog" aria-modal="true" aria-labelledby="delete-customer-title" onKeyDown={event => { if (event.key === "Escape" && !deleting) setDeleteTarget(null); }}><div className="c-modal-heading"><h2 id="delete-customer-title">Delete customer account?</h2><button disabled={deleting} aria-label="Close delete confirmation" onClick={() => setDeleteTarget(null)}>×</button></div><form className="c-form" onSubmit={deleteCustomer}><p><strong>{deleteTarget.name}</strong><br />{deleteTarget.email || deleteTarget.phone_number || deleteTarget.username}</p><div className="c-alert error">The account will be permanently removed and the customer will lose login access. This cannot be undone.</div><p>Existing orders, delivery addresses, payment references and stock records will stay in your business records. Orders will not be cancelled or refunded by deleting the account.</p>{deleteTarget.active_order_count > 0 && <p><strong>{deleteTarget.active_order_count} ongoing order(s)</strong> will still need fulfilment or cancellation from Online orders.</p>}{deleteError && <div className="c-alert error" role="alert">{deleteError}</div>}<label>Type DELETE to confirm<input autoFocus required autoComplete="off" value={confirmation} onChange={event => setConfirmation(event.target.value)} placeholder="DELETE" /></label><div className="c-modal-footer"><button type="button" className="c-button secondary" disabled={deleting} onClick={() => setDeleteTarget(null)}>Keep account</button><button className="c-button customer-danger" disabled={deleting || confirmation !== "DELETE"}>{deleting ? "Deleting…" : "Delete account"}</button></div></form></section></div>}
  </div>;
}
