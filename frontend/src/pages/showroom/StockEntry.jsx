import { useEffect, useState } from "react";
import { productApi, stockTransferApi, showroomStockApi } from "../../api/endpoints";

const todayStr = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
};

const listResults = (data) => data?.results ?? data ?? [];
const transferLabels = {
  sale: "Sale to Customer",
  receive: "Receive from Factory",
  factory_return: "Return to Factory",
  return: "Return from Customer",
};

export default function StockEntry() {
  const [products, setProducts] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [showroomStocks, setShowroomStocks] = useState({});
  const [date, setDate] = useState(todayStr());
  const [transferType, setTransferType] = useState("sale");
  const [editingTransferId, setEditingTransferId] = useState(null);
  const [deletingTransferId, setDeletingTransferId] = useState(null);
  const [form, setForm] = useState({ product: "", quantity: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    productApi.listAll({ is_active: true }).then(setProducts);
  }, []);

  function loadTransfers() {
    return stockTransferApi.list({ date }).then((res) => setTransfers(listResults(res.data)));
  }

  function loadStocks() {
    return showroomStockApi.list({}).then((res) => {
      const stocks = {};
      listResults(res.data).forEach((s) => {
        stocks[s.product] = s.quantity;
      });
      setShowroomStocks(stocks);
    });
  }

  useEffect(() => {
    loadTransfers();
    loadStocks();
  }, [date]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const quantity = parseInt(form.quantity, 10);
      if (isNaN(quantity) || quantity <= 0) {
        setError("Quantity must be a valid positive number.");
        return;
      }

      const productId = parseInt(form.product, 10);
      if (isNaN(productId)) {
        setError("Please select a product.");
        return;
      }

      const payload = {
        product: productId,
        quantity: quantity,
        transfer_type: transferType,
        date: date,
        notes: "",
      };

      if (editingTransferId) await stockTransferApi.update(editingTransferId, { quantity, transfer_type: transferType });
      else await stockTransferApi.create(payload);
      setSuccess(editingTransferId ? "Stock transfer updated." : `${transferLabels[transferType]} recorded successfully!`);
      setEditingTransferId(null);
      setForm({ product: "", quantity: "" });
      await Promise.all([loadTransfers(), loadStocks()]);
    } catch (err) {
      const response = err.response?.data;
      const validationErrors = response?.errors || response;
      const fieldMessages = validationErrors && typeof validationErrors === "object"
        ? Object.entries(validationErrors).flatMap(([field, messages]) => {
          const values = Array.isArray(messages) ? messages : [messages];
          return values.filter((message) => typeof message === "string")
            .map((message) => field === "non_field_errors" || field === "detail" ? message : `${field.replaceAll("_", " ")}: ${message}`);
        })
        : [];
      const errorMsg = fieldMessages.join(" ") || response?.detail ||
        "Could not save stock transfer. Check the quantities and try again.";
      setError(errorMsg);
      console.error("Transfer error:", err.response?.data);
    }
  }

  async function handleDelete(transfer) {
    if (!window.confirm("Delete this transfer? Stock quantities will be adjusted.")) return;
    setError("");
    setSuccess("");
    setDeletingTransferId(transfer.id);
    try {
      await stockTransferApi.delete(transfer.id);
      if (editingTransferId === transfer.id) {
        setEditingTransferId(null);
        setForm({ product: "", quantity: "" });
      }
      setSuccess("Stock transfer deleted.");
      await Promise.all([loadTransfers(), loadStocks()]);
    } catch (err) {
      const response = err.response?.data;
      const messages = response && typeof response === "object"
        ? Object.values(response).flatMap((value) => Array.isArray(value) ? value : [value]).filter((value) => typeof value === "string")
        : [];
      setError(messages.join(" ") || response?.detail || "Could not delete this transfer. Check the stock balance and try again.");
    } finally {
      setDeletingTransferId(null);
    }
  }

  const selectedProductId = form.product ? parseInt(form.product, 10) : null;
  const currentStock = selectedProductId ? showroomStocks[selectedProductId] || 0 : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Stock Management</h1>

      {                         }
      <div id="stock-transfer-form" className="bg-white rounded-2xl border border-gray-100 p-4 max-w-md">
        <label className="block text-xs text-gray-500 mb-1">Date</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          disabled={Boolean(editingTransferId)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4"
        />

        <label className="block text-xs text-gray-500 mb-1">Transfer Type</label>
        <select
          value={transferType}
          onChange={(e) => setTransferType(e.target.value)}
          className="w-full mb-4 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="sale">Sale to Customer</option>
          <option value="receive">Receive from Factory</option>
          <option value="factory_return">Return to Factory</option>
          <option value="return">Return from Customer</option>
        </select>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-2 mb-3">
              {error}
            </div>
          )}
          {success && (
            <div className="text-xs text-green-700 bg-green-50 border border-green-100 rounded px-2 py-2 mb-3">
              {success}
            </div>
          )}

          <label className="block text-xs text-gray-500 mb-1">Product</label>
          <select
            value={form.product}
            onChange={(e) => setForm({ ...form, product: e.target.value })}
            disabled={Boolean(editingTransferId)}
            className="w-full mb-3 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            required
          >
            <option value="">Select product</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} {p.size ? `(${p.size})` : ""}
              </option>
            ))}
          </select>

          {selectedProductId && transferType !== "receive" && (
            <div className="text-xs text-gray-600 bg-blue-50 border border-blue-100 rounded px-2 py-2 mb-3">
              Current stock: <strong>{currentStock} units</strong>
            </div>
          )}

          <label className="block text-xs text-gray-500 mb-1">Quantity</label>
          <input
            type="number"
            min="1"
            step="1"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            placeholder="Enter quantity"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4"
            required
          />

          <button
            type="submit"
            className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2 rounded-lg transition-colors"
          >
            {editingTransferId ? "Update stock transfer" : `Record ${transferLabels[transferType]}`}
          </button>
          {editingTransferId && <button type="button" onClick={() => { setEditingTransferId(null); setForm({ product: "", quantity: "" }); }} className="mt-2 w-full rounded-lg border border-gray-300 py-2 text-sm">Cancel edit</button>}
        </form>
      </div>

      {                     }
      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <div className="text-sm font-medium text-gray-700 mb-3">Transfers for {date}</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-100">
                <th className="py-2 px-2">Date</th>
                <th className="py-2 px-2">Product</th>
                <th className="py-2 px-2">Type</th>
                <th className="py-2 px-2 text-right">Quantity</th>
                <th className="py-2 px-2">From</th>
                <th className="py-2 px-2">To</th>
                <th className="py-2 px-2">Status</th>
                <th className="py-2 px-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {transfers.length > 0 ? (
                transfers.map((t) => (
                  <tr key={t.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 px-2 text-gray-500">{t.date}</td>
                    <td className="py-2 px-2">{t.product_name}</td>
                    <td className="py-2 px-2">
                      <span className={`text-xs font-semibold px-2 py-1 rounded ${
                        t.transfer_type === "receive" ? "bg-green-100 text-green-700" :
                        t.transfer_type === "sale" ? "bg-blue-100 text-blue-700" :
                        t.transfer_type === "factory_return" ? "bg-purple-100 text-purple-700" :
                        "bg-orange-100 text-orange-700"
                      }`}>
                        {transferLabels[t.transfer_type] || transferLabels.return}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-right font-medium">{t.quantity}</td>
                    <td className="py-2 px-2">{t.from_location}</td>
                    <td className="py-2 px-2">{t.to_location}</td>
                    <td className="py-2 px-2">
                      <span className="text-xs font-semibold px-2 py-1 rounded bg-green-100 text-green-700">
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => {
                            setEditingTransferId(t.id);
                            setForm({ product: String(t.product), quantity: String(t.quantity) });
                            setTransferType(t.transfer_type);
                            setError("");
                            setSuccess("");
                            document.getElementById("stock-transfer-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
                          }}
                          className="font-medium text-brand-700 hover:text-brand-900"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(t)}
                          disabled={deletingTransferId === t.id}
                          className="font-medium text-red-600 hover:text-red-800 disabled:opacity-50"
                        >
                          {deletingTransferId === t.id ? "Deleting…" : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="text-gray-400 py-4 text-center">
                    No transfers yet for this date.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
