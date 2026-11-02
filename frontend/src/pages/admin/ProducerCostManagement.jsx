import { useEffect, useMemo, useState } from "react";
import { producerApi } from "../../api/endpoints";

const money = (value) => `৳ ${Number(value || 0).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const asArray = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (!payload) return [];
  return Array.isArray(payload.results) ? payload.results : [];
};

function ModalShell({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5 py-4">
          <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100">Close</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export default function ProducerCostManagement() {
  const [summary, setSummary] = useState({ total_producer_cost: 0, total_other_cost: 0, grand_total_cost: 0, producer_count: 0 });
  const [producers, setProducers] = useState([]);
  const [producerCosts, setProducerCosts] = useState([]);
  const [producerPayments, setProducerPayments] = useState([]);
  const [otherCosts, setOtherCosts] = useState([]);
  const [costSpecs, setCostSpecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [producerForm, setProducerForm] = useState({ name: "", mobile_number: "", address: "" });
  const [producerModalOpen, setProducerModalOpen] = useState(false);
  const [editingProducer, setEditingProducer] = useState(null);

  const [producerCostForm, setProducerCostForm] = useState({
    producer: "",
    bale_number: "",
    product_specification: "",
    quantity: "",
    rate: "",
    gst_percentage: "",
    transaction_date: new Date().toISOString().slice(0, 10),
  });
  const [costModalOpen, setCostModalOpen] = useState(false);
  const [editingProducerCost, setEditingProducerCost] = useState(null);

  const [otherCostForm, setOtherCostForm] = useState({ specification: "", amount: "", cost_date: new Date().toISOString().slice(0, 10), notes: "" });
  const [otherCostModalOpen, setOtherCostModalOpen] = useState(false);
  const [editingOtherCost, setEditingOtherCost] = useState(null);

  const [paymentForm, setPaymentForm] = useState({ producer: "", payment_date: new Date().toISOString().slice(0, 10), amount: "", payment_method: "", remarks: "" });
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [editingPayment, setEditingPayment] = useState(null);

  const [producerSearch, setProducerSearch] = useState("");
  const [producerCostSearch, setProducerCostSearch] = useState("");
  const [otherCostSearch, setOtherCostSearch] = useState("");
  const [producerFilterDate, setProducerFilterDate] = useState("");
  const [otherFilterDateFrom, setOtherFilterDateFrom] = useState("");
  const [otherFilterDateTo, setOtherFilterDateTo] = useState("");
  const [selectedProducerId, setSelectedProducerId] = useState("");
  const [ledger, setLedger] = useState({ summary: {}, entries: [] });
  const [ledgerStart, setLedgerStart] = useState("");
  const [ledgerEnd, setLedgerEnd] = useState("");

  const producerSuggestions = useMemo(() => producers.filter((item) => item.name.toLowerCase().includes((producerSearch || "").toLowerCase())), [producers, producerSearch]);

  const calculateProducerCost = useMemo(() => {
    const quantity = Number(producerCostForm.quantity || 0);
    const rate = Number(producerCostForm.rate || 0);
    const gst = Number(producerCostForm.gst_percentage || 0);
    const baseCost = quantity * rate;
    const gstAmount = gst > 0 ? (baseCost * gst) / 100 : 0;
    return {
      baseCost,
      gstAmount,
      totalCost: baseCost + gstAmount,
    };
  }, [producerCostForm]);

  const fetchAll = async () => {
    setLoading(true);
    setError("");
    try {
      const [summaryRes, producersRes, producerCostsRes, paymentsRes, otherCostsRes, specRes] = await Promise.all([
        producerApi.dashboardSummary(),
        producerApi.list(),
        producerApi.costs.list(),
        producerApi.payments.list(),
        producerApi.otherCosts.list(),
        producerApi.costSpecifications.list(),
      ]);
      setSummary(summaryRes.data || { total_producer_cost: 0, total_other_cost: 0, grand_total_cost: 0, producer_count: 0 });
      setProducers(asArray(producersRes.data));
      setProducerCosts(asArray(producerCostsRes.data));
      setProducerPayments(asArray(paymentsRes.data));
      setOtherCosts(asArray(otherCostsRes.data));
      setCostSpecs(asArray(specRes.data));
    } catch (err) {
      setError("Unable to load producer and cost data.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const loadLedger = async (producerId, start = ledgerStart, end = ledgerEnd) => {
    if (!producerId) return;
    try {
      const res = await producerApi.ledger(producerId, { start_date: start || undefined, end_date: end || undefined });
      setLedger(res.data || { summary: {}, entries: [] });
    } catch (err) {
      console.error(err);
      setError("Unable to load producer ledger.");
    }
  };

  const handleProducerSubmit = async () => {
    const payload = { ...producerForm, name: producerForm.name.trim() };
    if (!payload.name) {
      alert("Producer name is required.");
      return;
    }
    try {
      if (editingProducer) {
        await producerApi.update(editingProducer.id, payload);
      } else {
        await producerApi.create(payload);
      }
      setProducerModalOpen(false);
      setProducerForm({ name: "", mobile_number: "", address: "" });
      setEditingProducer(null);
      await fetchAll();
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.name?.[0] || "Could not save producer.";
      alert(message);
    }
  };

  const handleProducerCostSubmit = async () => {
    const payload = {
      producer: Number(producerCostForm.producer),
      bale_number: producerCostForm.bale_number,
      product_specification: producerCostForm.product_specification,
      quantity: Number(producerCostForm.quantity || 0),
      rate: Number(producerCostForm.rate || 0),
      gst_percentage: Number(producerCostForm.gst_percentage || 0),
      transaction_date: producerCostForm.transaction_date,
    };
    if (!payload.producer) {
      alert("Please select a producer.");
      return;
    }
    if (!payload.product_specification && !payload.bale_number && !payload.quantity && !payload.rate) {
      alert("Provide at least the producer and transaction details before saving.");
      return;
    }
    if (Number(payload.quantity) <= 0 || Number(payload.rate) < 0) {
      alert("Quantity must be greater than zero and rate cannot be negative.");
      return;
    }
    try {
      if (editingProducerCost) {
        await producerApi.costs.update(editingProducerCost.id, payload);
      } else {
        await producerApi.costs.create(payload);
      }
      setCostModalOpen(false);
      setEditingProducerCost(null);
      setProducerCostForm({
        producer: "",
        bale_number: "",
        product_specification: "",
        quantity: "",
        rate: "",
        gst_percentage: "",
        transaction_date: new Date().toISOString().slice(0, 10),
      });
      await fetchAll();
      if (selectedProducerId) await loadLedger(selectedProducerId);
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.quantity?.[0] || "Could not save producer cost.";
      alert(message);
    }
  };

  const handleOtherCostSubmit = async () => {
    const payload = {
      specification_name: otherCostForm.specification.trim(),
      amount: Number(otherCostForm.amount || 0),
      cost_date: otherCostForm.cost_date,
      notes: otherCostForm.notes,
    };
    if (!payload.specification_name) {
      alert("Cost specification is required.");
      return;
    }
    if (Number(payload.amount) <= 0) {
      alert("Cost amount must be greater than zero.");
      return;
    }
    try {
      if (editingOtherCost) {
        await producerApi.otherCosts.update(editingOtherCost.id, payload);
      } else {
        await producerApi.otherCosts.create(payload);
      }
      setOtherCostModalOpen(false);
      setOtherCostForm({ specification: "", amount: "", cost_date: new Date().toISOString().slice(0, 10), notes: "" });
      setEditingOtherCost(null);
      await fetchAll();
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.amount?.[0] || "Could not save other cost.";
      alert(message);
    }
  };

  const handlePaymentSubmit = async () => {
    const payload = {
      producer: Number(paymentForm.producer),
      payment_date: paymentForm.payment_date,
      amount: Number(paymentForm.amount || 0),
      payment_method: paymentForm.payment_method,
      remarks: paymentForm.remarks,
    };
    if (!payload.producer) {
      alert("Producer is required.");
      return;
    }
    if (Number(payload.amount) <= 0) {
      alert("Payment amount must be greater than zero.");
      return;
    }
    try {
      if (editingPayment) {
        await producerApi.payments.update(editingPayment.id, payload);
      } else {
        await producerApi.payments.create(payload);
      }
      setPaymentModalOpen(false);
      setEditingPayment(null);
      setPaymentForm({ producer: selectedProducerId || "", payment_date: new Date().toISOString().slice(0, 10), amount: "", payment_method: "", remarks: "" });
      await fetchAll();
      if (selectedProducerId) await loadLedger(selectedProducerId);
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.amount?.[0] || "Could not save payment.";
      alert(message);
    }
  };

  const confirmDelete = async (promise) => {
    if (!window.confirm("This action will permanently hide the record without deleting the historical business data.")) return;
    await promise();
    await fetchAll();
    if (selectedProducerId) await loadLedger(selectedProducerId);
  };

  const filteredProducerCosts = producerCosts.filter((row) => {
    const itemSearch = `${row.producer_name || ""} ${row.bale_number || ""}`.toLowerCase();
    const matchesSearch = !producerCostSearch || itemSearch.includes(producerCostSearch.toLowerCase());
    const matchesDate = !producerFilterDate || row.transaction_date === producerFilterDate;
    return matchesSearch && matchesDate;
  });

  const filteredOtherCosts = otherCosts.filter((row) => {
    const itemSearch = `${row.specification_label || row.specification_name || ""} ${row.notes || ""}`.toLowerCase();
    const matchesSearch = !otherCostSearch || itemSearch.includes(otherCostSearch.toLowerCase());
    const matchesFrom = !otherFilterDateFrom || row.cost_date >= otherFilterDateFrom;
    const matchesTo = !otherFilterDateTo || row.cost_date <= otherFilterDateTo;
    return matchesSearch && matchesFrom && matchesTo;
  });

  const openProducerEditor = (producer) => {
    setEditingProducer(producer);
    setProducerForm({ name: producer.name, mobile_number: producer.mobile_number || "", address: producer.address || "" });
    setProducerModalOpen(true);
  };

  const openProducerCostEditor = (entry) => {
    setEditingProducerCost(entry);
    setProducerCostForm({
      producer: entry.producer || entry.producer_id || "",
      bale_number: entry.bale_number || "",
      product_specification: entry.product_specification || "",
      quantity: entry.quantity ? String(entry.quantity) : "",
      rate: entry.rate ? String(entry.rate) : "",
      gst_percentage: entry.gst_percentage ? String(entry.gst_percentage) : "",
      transaction_date: entry.transaction_date || new Date().toISOString().slice(0, 10),
    });
    setCostModalOpen(true);
  };

  const openPaymentEditor = (entry) => {
    setEditingPayment(entry);
    setPaymentForm({
      producer: entry.producer || selectedProducerId || "",
      payment_date: entry.payment_date || new Date().toISOString().slice(0, 10),
      amount: entry.amount ? String(entry.amount) : "",
      payment_method: entry.payment_method || "",
      remarks: entry.remarks || "",
    });
    setPaymentModalOpen(true);
  };

  const openOtherCostEditor = (entry) => {
    setEditingOtherCost(entry);
    setOtherCostForm({
      specification: entry.specification_label || entry.specification_name || "",
      amount: entry.amount ? String(entry.amount) : "",
      cost_date: entry.cost_date || new Date().toISOString().slice(0, 10),
      notes: entry.notes || "",
    });
    setOtherCostModalOpen(true);
  };

  const handleProducerSelection = async (value) => {
    const selected = producers.find((item) => item.name === value) || producers.find((item) => String(item.id) === String(value));
    const nextId = selected ? selected.id : value;
    setSelectedProducerId(nextId);
    setProducerSearch(value || "");
    if (nextId) await loadLedger(nextId);
  };

  if (loading) {
    return <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm font-medium text-slate-600">Loading producer cost dashboard...</div>;
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">Finance</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Producer &amp; Cost Management</h1>
        </div>
        <button
          type="button"
          onClick={() => setProducerModalOpen(true)}
          className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
        >
          Add Producer
        </button>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Total Producer Cost</p>
            <div className="mt-2 text-2xl font-bold text-slate-900">{money(summary.total_producer_cost)}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Total Others Cost</p>
            <div className="mt-2 text-2xl font-bold text-slate-900">{money(summary.total_other_cost)}</div>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-emerald-700">Grand Total Cost</p>
            <div className="mt-2 text-2xl font-bold text-emerald-800">{money(summary.grand_total_cost)}</div>
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-slate-900">Producer Cost and Others Cost</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setCostModalOpen(true)} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">Producer Cost</button>
            <button type="button" onClick={() => setOtherCostModalOpen(true)} className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Others Cost</button>
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Producer Cost and Others Cost History</h2>
            <p className="text-sm text-slate-500">Date-wise tracking and export of all producer and expense records.</p>
          </div>
          <button type="button" onClick={() => producerApi.export()} className="rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">Export Excel (.xlsx)</button>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">Producer Cost History</h3>
              <span className="rounded-full bg-brand-100 px-2 py-1 text-xs font-semibold text-brand-700">{producerCosts.length}</span>
            </div>
            <div className="mb-3 flex gap-2">
              <input value={producerCostSearch} onChange={(e) => setProducerCostSearch(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Search producer name or bale" />
              <input type="date" value={producerFilterDate} onChange={(e) => setProducerFilterDate(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
                <thead>
                  <tr className="bg-slate-100 text-slate-700">
                    <th className="border-b border-slate-200 px-3 py-2">Date</th>
                    <th className="border-b border-slate-200 px-3 py-2">Producer</th>
                    <th className="border-b border-slate-200 px-3 py-2">Bale</th>
                    <th className="border-b border-slate-200 px-3 py-2">Spec</th>
                    <th className="border-b border-slate-200 px-3 py-2">Qty</th>
                    <th className="border-b border-slate-200 px-3 py-2">Rate</th>
                    <th className="border-b border-slate-200 px-3 py-2">GST %</th>
                    <th className="border-b border-slate-200 px-3 py-2">Total</th>
                    <th className="border-b border-slate-200 px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducerCosts.map((row) => (
                    <tr key={row.id} className="even:bg-slate-50">
                      <td className="border-b border-slate-200 px-3 py-2">{row.transaction_date}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.producer_name}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.bale_number || "-"}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.product_specification || "-"}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.quantity}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{money(row.rate)}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.gst_percentage || 0}</td>
                      <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(row.total_cost)}</td>
                      <td className="border-b border-slate-200 px-3 py-2">
                        <div className="flex gap-2">
                          <button type="button" onClick={() => openProducerCostEditor(row)} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                          <button type="button" onClick={() => confirmDelete(() => producerApi.costs.delete(row.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">Others Cost History</h3>
              <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">{otherCosts.length}</span>
            </div>
            <div className="mb-3 flex gap-2">
              <input value={otherCostSearch} onChange={(e) => setOtherCostSearch(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" placeholder="Search cost specification" />
              <input type="date" value={otherFilterDateFrom} onChange={(e) => setOtherFilterDateFrom(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input type="date" value={otherFilterDateTo} onChange={(e) => setOtherFilterDateTo(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
                <thead>
                  <tr className="bg-slate-100 text-slate-700">
                    <th className="border-b border-slate-200 px-3 py-2">Date</th>
                    <th className="border-b border-slate-200 px-3 py-2">Specification</th>
                    <th className="border-b border-slate-200 px-3 py-2">Amount</th>
                    <th className="border-b border-slate-200 px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOtherCosts.map((row) => (
                    <tr key={row.id} className="even:bg-slate-50">
                      <td className="border-b border-slate-200 px-3 py-2">{row.cost_date}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{row.specification_label || row.specification_name || "-"}</td>
                      <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(row.amount)}</td>
                      <td className="border-b border-slate-200 px-3 py-2">
                        <div className="flex gap-2">
                          <button type="button" onClick={() => openOtherCostEditor(row)} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                          <button type="button" onClick={() => confirmDelete(() => producerApi.otherCosts.delete(row.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">All Producers Details</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="bg-slate-100 text-slate-700">
                <th className="border-b border-slate-200 px-3 py-2">Producer Name</th>
                <th className="border-b border-slate-200 px-3 py-2">Mobile Number</th>
                <th className="border-b border-slate-200 px-3 py-2">Address</th>
                <th className="border-b border-slate-200 px-3 py-2">Total Products</th>
                <th className="border-b border-slate-200 px-3 py-2">Total Cost</th>
                <th className="border-b border-slate-200 px-3 py-2">Total Paid</th>
                <th className="border-b border-slate-200 px-3 py-2">Due Amount</th>
                <th className="border-b border-slate-200 px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {producers.map((producer) => (
                <tr key={producer.id} className="even:bg-slate-50">
                  <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{producer.name}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{producer.mobile_number || "-"}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{producer.address || "-"}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{producer.total_products}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{money(producer.total_cost)}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{money(producer.total_paid)}</td>
                  <td className="border-b border-slate-200 px-3 py-2 font-medium text-rose-700">{money(producer.due_amount)}</td>
                  <td className="border-b border-slate-200 px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={async () => { setSelectedProducerId(producer.id); setProducerSearch(producer.name); await loadLedger(producer.id); }} className="text-xs font-medium text-brand-700 hover:underline">View Details</button>
                      <button type="button" onClick={() => openProducerEditor(producer)} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                      <button type="button" onClick={() => confirmDelete(() => producerApi.delete(producer.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Producer-wise Ledger</h2>
            <p className="text-sm text-slate-500">Select a producer and review date-wise cash and cost movement.</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input list="producer-ledger-suggestions" value={producerSearch} onChange={(e) => setProducerSearch(e.target.value)} placeholder="Search producer name" className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm sm:w-72" />
            <datalist id="producer-ledger-suggestions">
              {producers.map((producer) => (<option key={producer.id} value={producer.name} />))}
            </datalist>
            <button type="button" onClick={() => handleProducerSelection(producerSearch)} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">Load Ledger</button>
            {selectedProducerId && (
              <button type="button" onClick={() => { setPaymentForm({ producer: selectedProducerId, payment_date: new Date().toISOString().slice(0, 10), amount: "", payment_method: "", remarks: "" }); setPaymentModalOpen(true); }} className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Payment</button>
            )}
          </div>
        </div>

        {selectedProducerId && (
          <>
            <div className="grid gap-3 md:grid-cols-5">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><p className="text-xs uppercase tracking-wide text-slate-500">Opening Balance</p><div className="mt-1 text-lg font-bold text-slate-900">{money(ledger.summary?.opening_balance || 0)}</div></div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><p className="text-xs uppercase tracking-wide text-slate-500">Total Product Qty</p><div className="mt-1 text-lg font-bold text-slate-900">{ledger.summary?.total_product_quantity || 0}</div></div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><p className="text-xs uppercase tracking-wide text-slate-500">Total Producer Cost</p><div className="mt-1 text-lg font-bold text-slate-900">{money(ledger.summary?.total_producer_cost || 0)}</div></div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3"><p className="text-xs uppercase tracking-wide text-slate-500">Total Payments</p><div className="mt-1 text-lg font-bold text-slate-900">{money(ledger.summary?.total_payments || 0)}</div></div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3"><p className="text-xs uppercase tracking-wide text-emerald-700">Closing Balance</p><div className="mt-1 text-lg font-bold text-emerald-800">{money(ledger.summary?.closing_balance || 0)}</div></div>
            </div>

            <div className="flex gap-2">
              <input type="date" value={ledgerStart} onChange={(e) => setLedgerStart(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <input type="date" value={ledgerEnd} onChange={(e) => setLedgerEnd(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
              <button type="button" onClick={() => loadLedger(selectedProducerId, ledgerStart, ledgerEnd)} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Filter</button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
                <thead>
                  <tr className="bg-slate-100 text-slate-700">
                    <th className="border-b border-slate-200 px-3 py-2">Action</th>
                    <th className="border-b border-slate-200 px-3 py-2">Date</th>
                    <th className="border-b border-slate-200 px-3 py-2">Transaction Type</th>
                    <th className="border-b border-slate-200 px-3 py-2">Bale No</th>
                    <th className="border-b border-slate-200 px-3 py-2">Product Specification</th>
                    <th className="border-b border-slate-200 px-3 py-2">Qty</th>
                    <th className="border-b border-slate-200 px-3 py-2">Rate</th>
                    <th className="border-b border-slate-200 px-3 py-2">GST</th>
                    <th className="border-b border-slate-200 px-3 py-2">Debit</th>
                    <th className="border-b border-slate-200 px-3 py-2">Credit</th>
                    <th className="border-b border-slate-200 px-3 py-2">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.entries.map((entry) => (
                    <tr key={`${entry.kind}-${entry.id}`} className="even:bg-slate-50">
                      <td className="border-b border-slate-200 px-3 py-2">
                        {entry.kind === "cost" ? (
                          <div className="flex gap-2">
                            <button type="button" onClick={() => openProducerCostEditor({ ...entry, producer: selectedProducerId, producer_name: producers.find((p) => p.id === selectedProducerId)?.name || "" })} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                            <button type="button" onClick={() => confirmDelete(() => producerApi.costs.delete(entry.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button type="button" onClick={() => openPaymentEditor({ ...entry, producer: selectedProducerId, payment_method: entry.payment_method || "", remarks: entry.product_specification || "" })} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                            <button type="button" onClick={() => confirmDelete(() => producerApi.payments.delete(entry.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                          </div>
                        )}
                      </td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.date}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.transaction_type}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.bale_no || "-"}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.product_specification || "-"}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.quantity || 0}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{money(entry.rate || 0)}</td>
                      <td className="border-b border-slate-200 px-3 py-2">{entry.gst || 0}%</td>
                      <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(entry.debit || 0)}</td>
                      <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(entry.credit || 0)}</td>
                      <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(entry.balance || 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Others Cost History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="bg-slate-100 text-slate-700">
                <th className="border-b border-slate-200 px-3 py-2">Action</th>
                <th className="border-b border-slate-200 px-3 py-2">Date</th>
                <th className="border-b border-slate-200 px-3 py-2">Cost Specification</th>
                <th className="border-b border-slate-200 px-3 py-2">Amount</th>
              </tr>
            </thead>
            <tbody>
              {filteredOtherCosts.map((row) => (
                <tr key={`bottom-${row.id}`} className="even:bg-slate-50">
                  <td className="border-b border-slate-200 px-3 py-2">
                    <div className="flex gap-2">
                      <button type="button" onClick={() => openOtherCostEditor(row)} className="text-xs font-medium text-brand-700 hover:underline">Update</button>
                      <button type="button" onClick={() => confirmDelete(() => producerApi.otherCosts.delete(row.id))} className="text-xs font-medium text-rose-600 hover:underline">Delete</button>
                    </div>
                  </td>
                  <td className="border-b border-slate-200 px-3 py-2">{row.cost_date}</td>
                  <td className="border-b border-slate-200 px-3 py-2">{row.specification_label || row.specification_name || "-"}</td>
                  <td className="border-b border-slate-200 px-3 py-2 font-medium text-slate-800">{money(row.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {producerModalOpen && (
        <ModalShell title={editingProducer ? "Update Producer" : "Add Producer"} onClose={() => { setProducerModalOpen(false); setEditingProducer(null); setProducerForm({ name: "", mobile_number: "", address: "" }); }}>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Producer Name</label>
              <input value={producerForm.name} onChange={(e) => setProducerForm({ ...producerForm, name: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Producer Name" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Mobile Number</label>
              <input value={producerForm.mobile_number} onChange={(e) => setProducerForm({ ...producerForm, mobile_number: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Mobile Number" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Address</label>
              <textarea value={producerForm.address} onChange={(e) => setProducerForm({ ...producerForm, address: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" rows="4" placeholder="Address" />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setProducerModalOpen(false); setEditingProducer(null); setProducerForm({ name: "", mobile_number: "", address: "" }); }} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              <button type="button" onClick={handleProducerSubmit} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Save Producer</button>
            </div>
          </div>
        </ModalShell>
      )}

      {costModalOpen && (
        <ModalShell title={editingProducerCost ? "Update Producer Cost" : "Producer Cost"} onClose={() => { setCostModalOpen(false); setEditingProducerCost(null); setProducerCostForm({ producer: "", bale_number: "", product_specification: "", quantity: "", rate: "", gst_percentage: "", transaction_date: new Date().toISOString().slice(0, 10) }); }}>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Producer Name</label>
              <select value={producerCostForm.producer} onChange={(e) => setProducerCostForm({ ...producerCostForm, producer: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5">
                <option value="">Select producer</option>
                {producers.map((producer) => <option key={producer.id} value={producer.id}>{producer.name}</option>)}
              </select>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Bale Number</label>
                <input value={producerCostForm.bale_number} onChange={(e) => setProducerCostForm({ ...producerCostForm, bale_number: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Product Specification</label>
                <input value={producerCostForm.product_specification} onChange={(e) => setProducerCostForm({ ...producerCostForm, product_specification: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Quantity</label>
                <input type="number" step="0.01" value={producerCostForm.quantity} onChange={(e) => setProducerCostForm({ ...producerCostForm, quantity: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Rate</label>
                <input type="number" step="0.01" value={producerCostForm.rate} onChange={(e) => setProducerCostForm({ ...producerCostForm, rate: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">GST Percentage</label>
                <input type="number" step="0.01" value={producerCostForm.gst_percentage} onChange={(e) => setProducerCostForm({ ...producerCostForm, gst_percentage: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Date</label>
                <input type="date" value={producerCostForm.transaction_date} onChange={(e) => setProducerCostForm({ ...producerCostForm, transaction_date: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
            </div>

            <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-3">
              <div><p className="text-xs uppercase tracking-wide text-slate-500">Base Cost</p><p className="mt-1 text-lg font-bold text-slate-900">{money(calculateProducerCost.baseCost)}</p></div>
              <div><p className="text-xs uppercase tracking-wide text-slate-500">GST Amount</p><p className="mt-1 text-lg font-bold text-slate-900">{money(calculateProducerCost.gstAmount)}</p></div>
              <div><p className="text-xs uppercase tracking-wide text-slate-500">Total Cost</p><p className="mt-1 text-lg font-bold text-brand-700">{money(calculateProducerCost.totalCost)}</p></div>
            </div>

            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setCostModalOpen(false); setEditingProducerCost(null); setProducerCostForm({ producer: "", bale_number: "", product_specification: "", quantity: "", rate: "", gst_percentage: "", transaction_date: new Date().toISOString().slice(0, 10) }); }} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              <button type="button" onClick={handleProducerCostSubmit} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Save Producer Cost</button>
            </div>
          </div>
        </ModalShell>
      )}

      {otherCostModalOpen && (
        <ModalShell title={editingOtherCost ? "Update Other Cost" : "Others Cost"} onClose={() => { setOtherCostModalOpen(false); setEditingOtherCost(null); setOtherCostForm({ specification: "", amount: "", cost_date: new Date().toISOString().slice(0, 10), notes: "" }); }}>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Cost Specification</label>
              <input list="cost-specification-options" value={otherCostForm.specification} onChange={(e) => setOtherCostForm({ ...otherCostForm, specification: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Type or pick a cost specification" />
              <datalist id="cost-specification-options">
                {costSpecs.map((spec) => <option key={spec.id} value={spec.name} />)}
              </datalist>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Cost Amount</label>
                <input type="number" step="0.01" value={otherCostForm.amount} onChange={(e) => setOtherCostForm({ ...otherCostForm, amount: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Date</label>
                <input type="date" value={otherCostForm.cost_date} onChange={(e) => setOtherCostForm({ ...otherCostForm, cost_date: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Notes</label>
              <textarea value={otherCostForm.notes} onChange={(e) => setOtherCostForm({ ...otherCostForm, notes: e.target.value })} rows="3" className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Optional notes" />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setOtherCostModalOpen(false); setEditingOtherCost(null); setOtherCostForm({ specification: "", amount: "", cost_date: new Date().toISOString().slice(0, 10), notes: "" }); }} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              <button type="button" onClick={handleOtherCostSubmit} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Save Others Cost</button>
            </div>
          </div>
        </ModalShell>
      )}

      {paymentModalOpen && (
        <ModalShell title={editingPayment ? "Update Producer Payment" : "Add Producer Payment"} onClose={() => { setPaymentModalOpen(false); setEditingPayment(null); setPaymentForm({ producer: selectedProducerId || "", payment_date: new Date().toISOString().slice(0, 10), amount: "", payment_method: "", remarks: "" }); }}>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Producer Name</label>
              <input value={producers.find((p) => String(p.id) === String(paymentForm.producer))?.name || selectedProducerId ? producers.find((p) => String(p.id) === String(paymentForm.producer || selectedProducerId))?.name || "" : ""} readOnly className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Payment Date</label>
                <input type="date" value={paymentForm.payment_date} onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Payment Amount</label>
                <input type="number" step="0.01" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Payment Method</label>
                <input value={paymentForm.payment_method} onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Cash, Bank, Bkash" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Remarks</label>
                <input value={paymentForm.remarks} onChange={(e) => setPaymentForm({ ...paymentForm, remarks: e.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5" placeholder="Optional remarks" />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setPaymentModalOpen(false); setEditingPayment(null); setPaymentForm({ producer: selectedProducerId || "", payment_date: new Date().toISOString().slice(0, 10), amount: "", payment_method: "", remarks: "" }); }} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              <button type="button" onClick={handlePaymentSubmit} className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white">Save Payment</button>
            </div>
          </div>
        </ModalShell>
      )}
    </div>
  );
}
