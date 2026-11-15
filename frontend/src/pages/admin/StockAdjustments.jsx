import { useEffect, useState } from "react";
import { productApi, factoryStockApi, showroomApi, showroomStockApi, stockAdjustmentApi, onlineProductApi, onlineStockAdjustmentApi } from "../../api/endpoints";
import TableActionMenu from "../../components/TableActionMenu.jsx";
import { errorMessage } from "../../utils/apiError";

const listData = (response) => response.data.results || response.data;

export default function StockAdjustments({ online = false }) {
  const adjustmentApi = online ? onlineStockAdjustmentApi : stockAdjustmentApi;
  const [products, setProducts] = useState([]);
  const [productCodeSearch, setProductCodeSearch] = useState("");
  const [showrooms, setShowrooms] = useState([]);
  const [stocks, setStocks] = useState({});
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState({ product: "", location: "factory", showroom: "", new_quantity: "", reason: "" });
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [editForm, setEditForm] = useState({ new_quantity: "", reason: "" });

  async function updateAdjustment(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      await adjustmentApi.update(editing.id, { ...editForm, new_quantity: Number(editForm.new_quantity) });
      setEditing(null);
      setMessage("Adjustment corrected and stock recalculated.");
      await load();
    } catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  }

  async function deleteAdjustment(row) {
    if (busy || !window.confirm(`Delete the adjustment for ${row.product_name}? Its stock change (${row.difference > 0 ? "+" : ""}${row.difference}) will be reversed while preserving later stock movements.`)) return;
    setBusy(true);
    setMessage("");
    try {
      await adjustmentApi.delete(row.id);
      setMessage("Adjustment deleted and its stock change reversed.");
      await load();
    } catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  }

  async function load() {
    const [productRes, factoryRes, showroomRes, showroomStockRes, historyRes] = await Promise.all([
      (online ? onlineProductApi : productApi).listAll(), online ? Promise.resolve({ data: [] }) : factoryStockApi.list({ page_size: 200 }), showroomApi.list({ page_size: 200 }), showroomStockApi.list({ page_size: 200 }), adjustmentApi.list({ page_size: 200 }),
    ]);
    const productRows = productRes;
    const showroomRows = listData(showroomRes);
    const stockRows = {};
    (online ? productRows.map(p => ({ product: p.id, quantity: p.online_quantity })) : listData(factoryRes)).forEach((row) => { stockRows[`factory-${row.product}`] = row.quantity; });
    listData(showroomStockRes).forEach((row) => { stockRows[`showroom-${row.showroom}-${row.product}`] = row.quantity; });
    setProducts(productRows);
    setShowrooms(showroomRows);
    setStocks(stockRows);
    setHistory(listData(historyRes));
    setForm((current) => ({ ...current, product: current.product || String(productRows[0]?.id || ""), showroom: current.showroom || String(showroomRows[0]?.id || "") }));
  }

  useEffect(() => { load().catch(() => setMessage("Could not load stock data.")); }, [online]);

  const stockKey = form.location === "factory" ? `factory-${form.product}` : `showroom-${form.showroom}-${form.product}`;
  const currentQuantity = stocks[stockKey] ?? 0;
  const codeQuery = productCodeSearch.trim().toLowerCase();
  const matchingProducts = codeQuery
    ? products.filter((product) => String(product.code || "").toLowerCase().includes(codeQuery))
    : [];

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      await adjustmentApi.create({
        ...form,
        product: Number(form.product),
        showroom: form.location === "showroom" ? Number(form.showroom) : null,
        new_quantity: Number(form.new_quantity),
      });
      setMessage("Stock updated and adjustment recorded.");
      setForm((current) => ({ ...current, new_quantity: "", reason: "" }));
      await load();
    } catch (error) {
      setMessage(errorMessage(error));
    } finally { setBusy(false); }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">{online ? "Online stock adjustment" : "Product Stock Adjustment"}</h1>
        <p className="text-sm text-gray-500 mt-1">{online ? "Dedicated stock for website orders. Main and showroom inventory stay separate." : "Choose one inventory location. Other showrooms remain unchanged."}</p>
      </div>
      <form onSubmit={submit} className="grid gap-4 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="sm:col-span-2 lg:col-span-3">
          <label className="text-sm text-gray-600" htmlFor="stock-product-code">Search by product code</label>
          <input id="stock-product-code" type="search" value={productCodeSearch} onChange={(event) => setProductCodeSearch(event.target.value)} placeholder="Enter product code" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900" />
          {codeQuery && (
            <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-gray-200">
              {matchingProducts.length ? matchingProducts.map((product) => (
                <button key={product.id} type="button" onClick={() => { setForm((current) => ({ ...current, product: String(product.id) })); setProductCodeSearch(""); }} className={`block w-full px-3 py-2 text-left text-sm hover:bg-gray-50 ${String(product.id) === form.product ? "bg-gray-50 font-semibold" : ""}`}>
                  {product.code} · {product.name}{product.size ? ` · ${product.size}` : ""}
                </button>
              )) : <p role="status" className="px-3 py-2 text-sm text-gray-500">No products found for this code.</p>}
            </div>
          )}
        </div>
        <label className="text-sm text-gray-600">Product
          <select required value={form.product} onChange={(event) => setForm({ ...form, product: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            {products.map((product) => <option key={product.id} value={product.id}>{product.name}{product.code ? ` · ${product.code}` : ""}{product.size ? ` · ${product.size}` : ""}</option>)}
          </select>
        </label>
        <label className="text-sm text-gray-600">Inventory location
          <select value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            <option value="factory">{online ? "Online inventory" : "Factory stock"}</option>{!online && <option value="showroom">Showroom stock</option>}
          </select>
        </label>
        {form.location === "showroom" && <label className="text-sm text-gray-600">Showroom
          <select required value={form.showroom} onChange={(event) => setForm({ ...form, showroom: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900">
            {showrooms.map((showroom) => <option key={showroom.id} value={showroom.id}>{showroom.name}</option>)}
          </select>
        </label>}
        <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">Current quantity <strong className="ml-2 text-gray-900">{currentQuantity} pcs</strong></div>
        <label className="text-sm text-gray-600">New quantity
          <input required type="number" min="0" step="1" value={form.new_quantity} onChange={(event) => setForm({ ...form, new_quantity: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900" />
        </label>
        <label className="text-sm text-gray-600 sm:col-span-2 lg:col-span-3">Reason
          <input required value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} placeholder="e.g. Physical inventory count" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900" />
        </label>
        <div className="flex items-center gap-4 sm:col-span-2 lg:col-span-3">
          <button disabled={busy} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50">Save adjustment</button>
          {form.new_quantity !== "" && <span className="text-sm text-gray-600">Updated: <strong className="text-gray-900">{form.new_quantity} pcs</strong> ({Number(form.new_quantity) - currentQuantity >= 0 ? "+" : ""}{Number(form.new_quantity) - currentQuantity})</span>}
        </div>
      </form>
      {message && <p role="status" className="text-sm text-gray-600">{message}</p>}
      {editing && <form onSubmit={updateAdjustment} className="space-y-4 rounded-xl border border-gray-200 bg-white p-4">
        <h2 className="text-sm font-semibold">Update adjustment · {editing.product_name} · {editing.location === "factory" ? (online ? "Online" : "Factory") : editing.showroom_name}</h2>
        <p className="text-sm text-gray-500">Original quantity: {editing.previous_quantity} pcs. This corrects the original adjustment; later stock movements are preserved.</p>
        <label className="block text-sm text-gray-600">Corrected quantity<input autoFocus required type="number" min="0" step="1" value={editForm.new_quantity} onChange={event => setEditForm({ ...editForm, new_quantity: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" /></label>
        <label className="block text-sm text-gray-600">Reason<input required maxLength={255} value={editForm.reason} onChange={event => setEditForm({ ...editForm, reason: event.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" /></label>
        <div className="flex gap-3"><button disabled={busy} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? "Saving…" : "Save changes"}</button><button type="button" disabled={busy} onClick={() => setEditing(null)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm">Cancel</button></div>
      </form>}
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white">
        <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold">Adjustment history</h2>
        <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Last updated</th><th>Product</th><th>Location</th><th>Previous</th><th>Updated</th><th>Change</th><th>Reason</th><th>User</th><th className="px-4">Actions</th></tr></thead>
          <tbody>{history.map((row) => <tr key={row.id} className="border-t border-gray-100"><td className="px-4 py-3">{new Date(row.updated_at || row.created_at).toLocaleString()}</td><td>{row.product_name}</td><td>{row.location === "factory" ? (online ? "Online" : "Factory") : row.showroom_name}</td><td>{row.previous_quantity}</td><td>{row.new_quantity}</td><td>{row.difference > 0 ? `+${row.difference}` : row.difference}</td><td>{row.reason}</td><td>{row.created_by_name}</td><td className="px-4 py-3"><TableActionMenu><button type="button" disabled={busy} onClick={() => { setEditing(row); setEditForm({ new_quantity: String(row.new_quantity), reason: row.reason }); setMessage(""); }} className="text-brand-700">Update</button><button type="button" disabled={busy} onClick={() => deleteAdjustment(row)} className="text-red-700">Delete</button></TableActionMenu></td></tr>)}</tbody>
        </table></div>
      </section>
    </div>
  );
}
