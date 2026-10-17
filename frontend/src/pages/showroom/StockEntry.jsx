import { useEffect, useState } from "react";
import { productApi, stockApi } from "../../api/endpoints";

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function StockEntry() {
  const [products, setProducts] = useState([]);
  const [entries, setEntries] = useState([]);
  const [date, setDate] = useState(todayStr());
  const [form, setForm] = useState({ product: "", received_qty: 0, sold_qty: 0, return_qty: 0 });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    productApi.list({ is_active: true }).then((res) => setProducts(res.data.results || res.data));
  }, []);

  function loadEntries() {
    stockApi.list({ date }).then((res) => setEntries(res.data.results || res.data));
  }

  useEffect(loadEntries, [date]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await stockApi.create({ ...form, date });
      setSuccess("Stock entry saved.");
      setForm({ product: "", received_qty: 0, sold_qty: 0, return_qty: 0 });
      loadEntries();
    } catch (err) {
      setError(
        err.response?.data?.errors?.non_field_errors?.[0] ||
        err.response?.data?.detail ||
        "Could not save stock entry. Check the quantities."
      );
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Daily Stock Entry</h1>

      <div className="bg-white rounded-2xl border border-gray-100 p-4 max-w-md">
        <label className="block text-xs text-gray-500 mb-1">Date</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4" />

        <form onSubmit={handleSubmit}>
          {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
          {success && <div className="text-xs text-green-700 mb-2">{success}</div>}

          <label className="block text-xs text-gray-500 mb-1">Product</label>
          <select
            value={form.product}
            onChange={(e) => setForm({ ...form, product: e.target.value })}
            className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          >
            <option value="">Select product</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.name} {p.size ? `(${p.size})` : ""}</option>)}
          </select>

          <div className="grid grid-cols-3 gap-2 mb-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Received</label>
              <input type="number" min="0" value={form.received_qty} onChange={(e) => setForm({ ...form, received_qty: e.target.value })} className="w-full border border-gray-300 rounded-lg px-2 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Sold</label>
              <input type="number" min="0" value={form.sold_qty} onChange={(e) => setForm({ ...form, sold_qty: e.target.value })} className="w-full border border-gray-300 rounded-lg px-2 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Return</label>
              <input type="number" min="0" value={form.return_qty} onChange={(e) => setForm({ ...form, return_qty: e.target.value })} className="w-full border border-gray-300 rounded-lg px-2 py-2 text-sm" />
            </div>
          </div>

          <button className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2 rounded-lg">
            Save entry
          </button>
        </form>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <div className="text-sm font-medium text-gray-700 mb-2">Entries for {date}</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-1">Product</th><th>Opening</th><th>Received</th><th>Sold</th><th>Return</th><th>Closing</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} className="border-b border-gray-50">
                <td className="py-1">{e.product_name}</td><td>{e.opening_qty}</td><td>{e.received_qty}</td><td>{e.sold_qty}</td><td>{e.return_qty}</td><td className="font-medium">{e.closing_qty}</td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr><td colSpan={6} className="text-gray-400 py-3">No entries yet for this date.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
