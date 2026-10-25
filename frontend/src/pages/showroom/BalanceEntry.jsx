import { useEffect, useState } from "react";
import { balanceApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

const todayStr = () => localDateString();

function errorMessage(error) {
  const response = error.response?.data;
  const fieldErrors = response?.errors || {};
  const messages = Object.entries(fieldErrors).flatMap(([field, value]) =>
    (Array.isArray(value) ? value : [value]).filter((message) => typeof message === "string")
      .map((message) => field === "non_field_errors" ? message : `${field.replaceAll("_", " ")}: ${message}`)
  );
  return messages.join(" ") || response?.detail || "Could not save balance entry. Please check the values and try again.";
}

export default function BalanceEntry() {
  const [date, setDate] = useState(todayStr());
  const [existing, setExisting] = useState(null);
  const [form, setForm] = useState({ cash_sale: 0, card_sale: 0, expense: 0, salary: 0, deposit: 0, notes: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function loadEntry() {
    setError("");
    balanceApi.list({ date }).then((res) => {
      const results = res.data.results || res.data;
      const entry = results[0] || null;
      setExisting(entry);
      if (entry) setForm({ cash_sale: entry.cash_sale, card_sale: entry.card_sale, expense: entry.expense, salary: entry.salary, deposit: entry.deposit, notes: entry.notes || "" });
      else setForm({ cash_sale: 0, card_sale: 0, expense: 0, salary: 0, deposit: 0, notes: "" });
    }).catch((err) => {
      setExisting(null);
      setError(err.response?.data?.detail || "Could not load the balance entry for this date.");
    });
  }

  useEffect(loadEntry, [date]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      const payload = { ...form, date };
      if (existing) await balanceApi.update(existing.id, payload);
      else await balanceApi.create(payload);
      setSuccess(existing ? "Sales statement updated." : "Balance entry saved.");
      loadEntry();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Daily Balance Entry</h1>

      <div className="max-w-md">
        <label className="block text-xs text-gray-500 mb-1">Date</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4" />
      </div>

      {existing && (
        <div className="w-full max-w-xl bg-white rounded-2xl border border-gray-100 p-4">
          <div className="text-sm font-medium text-gray-700 mb-3">Already recorded for {date}</div>
          <table className="w-full table-fixed text-sm">
            <tbody>
              {[
                ["Opening Balance", existing.opening_balance],
                ["Cash Sale", existing.cash_sale],
                ["Card Sale", existing.card_sale],
                ["Total Sale", existing.total_sale],
                ["Expense", existing.expense],
                ["Salary", existing.salary],
                ["Deposit", existing.deposit],
                ["Notes", existing.notes || "—"],
                ["Closing Balance", existing.closing_balance],
              ].map(([label, val]) => (
                <tr key={label} className="border-b border-gray-50">
                  <td className="w-1/2 py-1 text-gray-500">{label}</td>
                  <td className={`w-1/2 ${label === "Notes" ? "text-left" : "whitespace-nowrap text-right"} font-medium`}>{label === "Notes" ? val : `৳ ${Number(val).toLocaleString()}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-100 p-4 max-w-md">
          {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
          {success && <div className="text-xs text-green-700 mb-2">{success}</div>}

          {[
            ["cash_sale", "Cash Sale"],
            ["card_sale", "Card Sale"],
            ["expense", "Expense"],
            ["salary", "Salary"],
            ["deposit", "Deposit"],
          ].map(([key, label]) => (
            <div key={key} className="mb-2">
              <label className="block text-xs text-gray-500 mb-1">{label}</label>
              <input
                type="number"
                min="0"
                max="100000"
                step="0.01"
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          ))}

          <label className="mb-2 block text-xs text-gray-500">Expense / other details (optional)
            <textarea maxLength={500} rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="e.g. shop rent, electricity, transport" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </label>

          <p className="text-xs text-gray-400 mb-3">
            Opening balance is carried forward automatically from yesterday's closing balance.
          </p>

          <button className="w-full bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium py-2 rounded-lg">
            {existing ? "Update statement" : "Save entry"}
          </button>
      </form>
    </div>
  );
}
