import { useEffect, useMemo, useState } from "react";
import { swingApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

const today = localDateString();
const blankOperator = { name: "", nid_number: "" };
const blankLot = { operator: "", lot_number: "", quantity: "", fabric_specification: "", rate: "", cutting_master_name: "", lot_date: today };
const blankPayment = { payment_date: today, amount: "", remarks: "" };
const blankReject = { lot: "", quantity: "", reject_date: today, remarks: "" };
const inputClass = "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-600";
const money = (value) => `৳ ${Number(value || 0).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const rowsOf = (response) => response.data.results || response.data;

function errorText(error) {
  const data = error.response?.data;
  if (!data) return "The request could not reach the server. Check your connection and try again.";
  if (data.errors) return Object.values(data.errors).flat().join(" ");
  if (typeof data === "string") return data;
  return data.detail || Object.values(data).flat().join(" ") || "The request failed.";
}

function Field({ label, children }) {
  return <label className="block text-xs font-medium text-gray-600">{label}{children}</label>;
}

function Modal({ title, onClose, children }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section role="dialog" aria-modal="true" aria-labelledby="swing-modal-title" className="max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white shadow-2xl">
      <header className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
        <h2 id="swing-modal-title" className="text-base font-semibold text-gray-900">{title}</h2>
        <button type="button" title="Close dialog" aria-label="Close dialog" onClick={onClose} className="flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-lg text-gray-600 hover:bg-gray-50">×</button>
      </header>
      {children}
    </section>
  </div>;
}

function SummaryCard({ label, value, loading, currency = false, accent }) {
  return <article className="dashboard-stat-card">
    <div className="flex items-start justify-between gap-3"><p className="dashboard-stat-label">{label}</p><span className={`dashboard-stat-mark border ${accent}`} aria-hidden="true" /></div>
    <p className="dashboard-stat-value">{loading ? "Loading…" : value === undefined ? "—" : currency ? money(value) : Number(value || 0).toLocaleString()}</p>
  </article>;
}

function TableEmpty({ children, columns }) {
  return <tr><td colSpan={columns} className="px-3 py-8 text-center text-sm text-gray-500">{children}</td></tr>;
}

export default function SwingManagement() {
  const [operators, setOperators] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [selectedOperator, setSelectedOperator] = useState("");
  const [operatorSearch, setOperatorSearch] = useState("");
  const [detailsSearch, setDetailsSearch] = useState("");
  const [operatorPickerOpen, setOperatorPickerOpen] = useState(false);
  const [statementData, setStatementData] = useState(null);
  const [modal, setModal] = useState("");
  const [editingOperator, setEditingOperator] = useState(null);
  const [editingLot, setEditingLot] = useState(null);
  const [editingPayment, setEditingPayment] = useState(null);
  const [editingReject, setEditingReject] = useState(null);
  const [operatorForm, setOperatorForm] = useState(blankOperator);
  const [lotForm, setLotForm] = useState(blankLot);
  const [lotOperatorSearch, setLotOperatorSearch] = useState("");
  const [paymentForm, setPaymentForm] = useState(blankPayment);
  const [rejectForm, setRejectForm] = useState(blankReject);
  const [lotSearch, setLotSearch] = useState("");
  const [lotPickerOpen, setLotPickerOpen] = useState(false);
  const [status, setStatus] = useState({ loading: true, detailLoading: false, saving: false, error: "", message: "" });

  const activeOperators = useMemo(() => operators.filter((operator) => operator.is_active), [operators]);
  const searchedOperators = useMemo(() => activeOperators.filter((operator) => operator.name.toLowerCase().includes(detailsSearch.toLowerCase())), [activeOperators, detailsSearch]);
  const dashboardRows = dashboard?.operators || [];
  const searchedDashboardRows = useMemo(() => dashboardRows.filter((operator) => operator.name.toLowerCase().includes(operatorSearch.toLowerCase())), [dashboardRows, operatorSearch]);
  const selected = statementData?.operator;
  const lots = statementData?.lots || [];
  const lotRows = statementData?.lot_rows || [];
  const statementEvents = statementData?.statement || [];
  const payments = statementEvents.filter((row) => row.event_type === "payment");
  const rejections = statementEvents.filter((row) => row.event_type === "reject");
  const selectedLot = lots.find((lot) => String(lot.id) === String(rejectForm.lot));
  const editedReject = rejections.find((row) => row.reject_id === editingReject);
  const availableForReject = selectedLot
    ? selectedLot.available_quantity + (editedReject?.lot_id === selectedLot.id ? editedReject.reject_qty : 0)
    : 0;
  const rejectAmount = selectedLot ? Number(rejectForm.quantity || 0) * Number(selectedLot.rate) : 0;
  const visibleLots = lots.filter((lot) => (lot.lot_number || `Lot ${lot.id}`).toLowerCase().includes(lotSearch.toLowerCase()));
  const lotOperators = activeOperators.filter((operator) => operator.name.toLowerCase().includes(lotOperatorSearch.toLowerCase()));

  async function loadOperators() {
    const response = await swingApi.operators.list();
    const rows = rowsOf(response);
    setOperators(rows);
    return rows;
  }

  async function loadDashboard() {
    const response = await swingApi.summary();
    setDashboard(response.data);
    return response.data;
  }

  async function loadStatement(operatorId = selectedOperator) {
    if (!operatorId) {
      setStatementData(null);
      return null;
    }
    const response = await swingApi.operators.statement(operatorId);
    setStatementData(response.data);
    return response.data;
  }

  async function refreshDashboard(operatorId = selectedOperator) {
    await Promise.all([loadOperators(), loadDashboard()]);
    if (operatorId) await loadStatement(operatorId);
  }

  useEffect(() => {
    Promise.all([loadOperators(), loadDashboard()])
      .catch((error) => setStatus((current) => ({ ...current, error: errorText(error) })))
      .finally(() => setStatus((current) => ({ ...current, loading: false })));
  }, []);

  useEffect(() => {
    if (!selectedOperator) {
      setStatementData(null);
      return;
    }
    setStatus((current) => ({ ...current, detailLoading: true, error: "" }));
    loadStatement(selectedOperator)
      .catch((error) => setStatus((current) => ({ ...current, error: errorText(error) })))
      .finally(() => setStatus((current) => ({ ...current, detailLoading: false })));
  }, [selectedOperator]);

  function notifyError(error) {
    setStatus((current) => ({ ...current, error: errorText(error), message: "" }));
  }

  function closeModal() {
    if (!status.saving) setModal("");
  }

  function openOperatorModal(operator = null) {
    setEditingOperator(operator?.id || null);
    setOperatorForm(operator ? { name: operator.name, nid_number: operator.nid_number || "" } : blankOperator);
    setModal("operator");
  }

  async function submitOperator(event) {
    event.preventDefault();
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      let operatorId = selectedOperator;
      if (editingOperator) {
        await swingApi.operators.update(editingOperator, operatorForm);
        setStatus((current) => ({ ...current, message: "Operator details updated." }));
      } else {
        const response = await swingApi.operators.create(operatorForm);
        operatorId = String(response.data.id);
        setSelectedOperator(operatorId);
        setDetailsSearch(response.data.name);
        setStatus((current) => ({ ...current, message: "Swing operator added." }));
      }
      setModal("");
      await refreshDashboard(operatorId);
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deleteOperator(operator) {
    if (!window.confirm(`Deactivate ${operator.name}? All lot, reject, and payment history will be preserved.`)) return;
    try {
      await swingApi.operators.delete(operator.id);
      const nextSelected = String(operator.id) === selectedOperator ? "" : selectedOperator;
      if (!nextSelected) {
        setSelectedOperator("");
        setDetailsSearch("");
      }
      await refreshDashboard(nextSelected);
      setStatus((current) => ({ ...current, message: `${operator.name} was deactivated; financial history was preserved.`, error: "" }));
    } catch (error) { notifyError(error); }
  }

  function openLotModal(lot = null) {
    setEditingLot(lot?.id || null);
    const operatorId = selectedOperator || "";
    setLotForm(lot ? {
      operator: operatorId,
      lot_number: lot.lot_number,
      quantity: String(lot.quantity),
      fabric_specification: lot.fabric_specification,
      rate: String(lot.rate),
      cutting_master_name: lot.cutting_master_name,
      lot_date: lot.lot_date,
    } : { ...blankLot, operator: operatorId, lot_date: today });
    setLotOperatorSearch(activeOperators.find((operator) => String(operator.id) === operatorId)?.name || "");
    setModal("lot");
  }

  async function submitLot(event) {
    event.preventDefault();
    if (!lotForm.operator) return;
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      const payload = {
        ...lotForm,
        operator: Number(lotForm.operator),
        quantity: Number(lotForm.quantity || 0),
        rate: lotForm.rate || "0",
      };
      if (editingLot) await swingApi.lots.update(editingLot, payload);
      else await swingApi.lots.create(payload);
      const operatorId = lotForm.operator;
      setModal("");
      setSelectedOperator(operatorId);
      await refreshDashboard(operatorId);
      setStatus((current) => ({ ...current, message: editingLot ? "Lot updated; balances recalculated." : "Production lot created." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deleteLot(lot) {
    if (!window.confirm(`Delete lot ${lot.lot_number || `#${lot.id}`} from active records? Related reject history will be preserved.`)) return;
    try {
      await swingApi.lots.delete(lot.id);
      await refreshDashboard();
      setStatus((current) => ({ ...current, message: "Lot deactivated and all balances recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  function openPayment(payment = null) {
    setEditingPayment(payment?.payment_id || null);
    setPaymentForm(payment ? {
      payment_date: payment.event_date,
      amount: String(payment.receive_tk),
      remarks: payment.remarks || "",
    } : { ...blankPayment, payment_date: today });
    setModal("payment");
  }

  async function submitPayment(event) {
    event.preventDefault();
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      const payload = { ...paymentForm, operator: Number(selectedOperator) };
      if (editingPayment) await swingApi.payments.update(editingPayment, payload);
      else await swingApi.payments.create(payload);
      setModal("");
      await refreshDashboard();
      setStatus((current) => ({ ...current, message: "Payment saved; dashboard and balances updated." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deletePayment(payment) {
    if (!window.confirm("Delete this payment from active records? Its payment history will be retained.")) return;
    try {
      await swingApi.payments.delete(payment.payment_id);
      await refreshDashboard();
      setStatus((current) => ({ ...current, message: "Payment deactivated and balances recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  function openReject(reject = null) {
    setEditingReject(reject?.reject_id || null);
    const lot = reject ? lots.find((row) => row.id === reject.lot_id) : null;
    setRejectForm(reject ? {
      lot: String(reject.lot_id),
      quantity: String(reject.reject_qty),
      reject_date: reject.event_date,
      remarks: reject.remarks || "",
    } : { ...blankReject, reject_date: today });
    setLotSearch(lot ? (lot.lot_number || `Lot ${lot.id}`) : "");
    setLotPickerOpen(false);
    setModal("reject");
  }

  async function submitReject(event) {
    event.preventDefault();
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      const payload = { ...rejectForm, lot: Number(rejectForm.lot), quantity: Number(rejectForm.quantity) };
      if (editingReject) await swingApi.rejects.update(editingReject, payload);
      else await swingApi.rejects.create(payload);
      setModal("");
      await refreshDashboard();
      setStatus((current) => ({ ...current, message: "Reject saved; accepted quantities and balances updated." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deleteReject(reject) {
    if (!window.confirm("Delete this rejection from active records? Its history will be retained.")) return;
    try {
      await swingApi.rejects.delete(reject.reject_id);
      await refreshDashboard();
      setStatus((current) => ({ ...current, message: "Rejection deactivated and balances recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  const currentOperatorName = selected?.name || activeOperators.find((operator) => String(operator.id) === selectedOperator)?.name || "";

  return <div className="space-y-6">
    <header className="dashboard-heading">
      <div><p className="dashboard-eyebrow">Production payroll</p><h1>Swing Management</h1><p className="mt-1 text-sm text-gray-600">Operator production, lot wages, rejections, and payments.</p></div>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => openOperatorModal()} className="rounded-lg border border-emerald-700 px-4 py-2.5 text-sm font-semibold text-emerald-800 hover:bg-emerald-50">Add Operator</button>
        <button type="button" onClick={() => openLotModal()} disabled={!activeOperators.length} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">Create Lot</button>
      </div>
    </header>

    {(status.error || status.message) && <div role={status.error ? "alert" : "status"} className={`whitespace-pre-line rounded-lg border p-3 text-sm ${status.error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{status.error || status.message}</div>}

    <section aria-label="All swing operators summary" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <SummaryCard label="Total products sewn" value={dashboard?.summary.total_products_sewn} loading={status.loading} accent="border-emerald-600 bg-emerald-50" />
      <SummaryCard label="Total sewing cost" value={dashboard?.summary.total_sewing_cost} loading={status.loading} currency accent="border-amber-600 bg-amber-50" />
      <SummaryCard label="Total payments made" value={dashboard?.summary.total_payments_made} loading={status.loading} currency accent="border-sky-600 bg-sky-50" />
      <SummaryCard label="Total outstanding due" value={dashboard?.summary.total_outstanding_due} loading={status.loading} currency accent="border-rose-600 bg-rose-50" />
    </section>

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>All Swing Operators</h2><p>Active operator totals from saved lots, rejections, and payments.</p></div><span className="dashboard-section-tag">{dashboardRows.length} active</span></div>
      <div className="mb-4 max-w-sm"><Field label="Search operators"><input className={inputClass} placeholder="Search by operator name" value={operatorSearch} onChange={(event) => setOperatorSearch(event.target.value)} /></Field></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="bg-gray-50 text-[11px] uppercase text-gray-600"><tr>{["Operator Name", "Total Products", "Rejected Products", "Total Work Amount", "Total Paid", "Total Due", "Actions"].map((heading) => <th key={heading} className="whitespace-nowrap px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">
        {searchedDashboardRows.map((operator) => <tr key={operator.id}><td className="whitespace-nowrap px-3 py-3 font-semibold text-gray-900">{operator.name}</td><td className="px-3 py-3">{Number(operator.total_products).toLocaleString()}</td><td className="px-3 py-3">{Number(operator.rejected_products).toLocaleString()}</td><td className="px-3 py-3">{money(operator.total_work_amount)}</td><td className="px-3 py-3">{money(operator.total_paid)}</td><td className="px-3 py-3 font-semibold">{money(operator.total_due)}</td><td className="px-3 py-3"><div className="flex gap-3"><button type="button" onClick={() => { setSelectedOperator(String(operator.id)); setDetailsSearch(activeOperators.find((row) => row.id === operator.id)?.name || operator.name); document.getElementById("swing-operator-details")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} className="whitespace-nowrap text-xs font-semibold text-emerald-800 hover:underline">View Details</button><button type="button" onClick={() => openOperatorModal(activeOperators.find((row) => row.id === operator.id))} className="text-xs font-semibold text-gray-700 hover:underline">Edit</button><button type="button" onClick={() => deleteOperator(operator)} className="text-xs font-semibold text-rose-700 hover:underline">Delete</button></div></td></tr>)}
        {!status.loading && !searchedDashboardRows.length && <TableEmpty columns={7}>{operatorSearch ? "No active operators match this search." : "No active swing operators yet."}</TableEmpty>}
        {status.loading && <TableEmpty columns={7}>Loading dashboard records…</TableEmpty>}
      </tbody></table></div>
    </section>

    <section id="swing-operator-details" className="space-y-4 scroll-mt-6">
      <div className="dashboard-section-heading"><div><h2>Operator Details</h2><p>{selected ? `${currentOperatorName} · chronological production and financial history` : "Search and select an operator to view their statement."}</p></div></div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="relative w-full sm:max-w-md"><Field label="Search swing operator"><input role="combobox" aria-expanded={operatorPickerOpen} aria-autocomplete="list" autoComplete="off" className={inputClass} placeholder="Type an operator name" value={detailsSearch} onFocus={() => setOperatorPickerOpen(true)} onBlur={() => window.setTimeout(() => setOperatorPickerOpen(false), 120)} onChange={(event) => { setDetailsSearch(event.target.value); setOperatorPickerOpen(true); }} /></Field>
          {operatorPickerOpen && <ul role="listbox" className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">{searchedOperators.map((operator) => <li key={operator.id}><button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => { setSelectedOperator(String(operator.id)); setDetailsSearch(operator.name); setOperatorPickerOpen(false); }} className={`w-full px-3 py-2 text-left text-sm hover:bg-emerald-50 ${selectedOperator === String(operator.id) ? "bg-emerald-50 font-semibold" : ""}`}>{operator.name}</button></li>)}{!searchedOperators.length && <li className="px-3 py-2 text-sm text-gray-500">No matching active operators</li>}</ul>}
        </div>
        <div className="flex gap-2"><button type="button" onClick={() => openPayment()} disabled={!selectedOperator} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">Payment</button><button type="button" onClick={() => openReject()} disabled={!selectedOperator || !lots.length} className="rounded-lg border border-rose-200 px-4 py-2.5 text-sm font-semibold text-rose-800 disabled:opacity-50">Reject Details</button></div>
      </div>

      {selectedOperator && <>
        <div className="grid grid-cols-2 gap-4 border-y border-gray-200 py-4 sm:grid-cols-3 xl:grid-cols-7">
          <div className="border-l-2 border-emerald-700 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Total lots</p><p className="mt-1 text-base font-semibold">{summaryValue("total_lots")}</p></div>
          <div className="border-l-2 border-sky-600 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Products assigned</p><p className="mt-1 text-base font-semibold">{summaryValue("total_products_assigned")}</p></div>
          <div className="border-l-2 border-rose-600 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Rejected quantity</p><p className="mt-1 text-base font-semibold">{summaryValue("total_rejected_quantity")}</p></div>
          <div className="border-l-2 border-emerald-700 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Accepted quantity</p><p className="mt-1 text-base font-semibold">{summaryValue("total_accepted_quantity")}</p></div>
          <div className="border-l-2 border-amber-600 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Net sewing amount</p><p className="mt-1 text-base font-semibold">{money(statementData?.summary.net_sewing_amount)}</p></div>
          <div className="border-l-2 border-sky-600 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Payments received</p><p className="mt-1 text-base font-semibold">{money(statementData?.summary.total_payments_received)}</p></div>
          <div className="border-l-2 border-rose-600 py-1 pl-3"><p className="text-[11px] font-semibold uppercase text-gray-500">Outstanding balance</p><p className="mt-1 text-base font-semibold">{money(statementData?.summary.current_outstanding_balance)}</p></div>
        </div>

        <section className="dashboard-chart-panel">
          <div className="dashboard-section-heading mb-3"><div><h3>Lot Details</h3><p>One row per lot; reject quantities and amounts are grouped by their lot.</p></div><button type="button" onClick={() => openLotModal()} className="rounded-lg border border-emerald-700 px-3 py-2 text-xs font-semibold text-emerald-800">Create Lot</button></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[1320px] text-left text-sm"><thead className="bg-gray-50 text-[11px] uppercase text-gray-600"><tr>{["Action", "Date", "B/F Taka", "Colour", "Lot No", "Lot QTY", "Lot Rate", "Total Tk", "Reject QTY", "Reject Tk", "Receive Tk", "Due Taka"].map((heading) => <th key={heading} className="whitespace-nowrap px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">{lotRows.map((row) => {
            const lot = lots.find((item) => item.id === row.lot_id);
            return <tr key={row.lot_id}><td className="whitespace-nowrap px-3 py-3"><div className="flex gap-3"><button type="button" onClick={() => openLotModal(lot)} className="text-xs font-semibold text-emerald-800">Update</button><button type="button" onClick={() => deleteLot(lot)} className="text-xs font-semibold text-rose-700">Delete</button></div></td><td className="whitespace-nowrap px-3 py-3">{row.event_date}</td><td className="px-3 py-3">{money(row.bf_taka)}</td><td className="px-3 py-3">{row.colour || "—"}</td><td className="px-3 py-3">{row.lot_no || "—"}</td><td className="px-3 py-3">{Number(row.lot_qty).toLocaleString()}</td><td className="px-3 py-3">{money(row.lot_rate)}</td><td className="px-3 py-3">{money(row.total_tk)}</td><td className="px-3 py-3">{Number(row.reject_qty).toLocaleString()}</td><td className="px-3 py-3">{money(row.reject_tk)}</td><td className="px-3 py-3">{money(row.receive_tk)}</td><td className="px-3 py-3 font-semibold">{money(row.due_taka)}</td></tr>;
          })}{status.detailLoading && <TableEmpty columns={12}>Loading lot details…</TableEmpty>}{!status.detailLoading && !lotRows.length && <TableEmpty columns={12}>No lots created for this operator.</TableEmpty>}</tbody></table></div>
        </section>

        <section className="dashboard-chart-panel">
          <div className="dashboard-section-heading mb-3"><div><h3>Payment History</h3><p>Payments are listed separately in date order and included once in the balance.</p></div></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-gray-50 text-[11px] uppercase text-gray-600"><tr>{["Action", "Payment Date", "Amount", "Remarks"].map((heading) => <th key={heading} className="px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">{payments.map((payment) => <tr key={payment.payment_id}><td className="px-3 py-3"><div className="flex gap-3"><button type="button" onClick={() => openPayment(payment)} className="text-xs font-semibold text-emerald-800">Update</button><button type="button" onClick={() => deletePayment(payment)} className="text-xs font-semibold text-rose-700">Delete</button></div></td><td className="px-3 py-3">{payment.event_date}</td><td className="px-3 py-3 font-medium">{money(payment.receive_tk)}</td><td className="px-3 py-3">{payment.remarks || "—"}</td></tr>)}{!payments.length && <TableEmpty columns={4}>No payments recorded for this operator.</TableEmpty>}</tbody></table></div>
        </section>

        <section className="dashboard-chart-panel">
          <div className="dashboard-section-heading mb-3"><div><h3>Reject History</h3><p>Rejected units remain associated with their original lot.</p></div></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-gray-50 text-[11px] uppercase text-gray-600"><tr>{["Action", "Reject Date", "Lot No", "Reject Quantity", "Reject Amount", "Remarks"].map((heading) => <th key={heading} className="px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">{rejections.map((reject) => <tr key={reject.reject_id}><td className="px-3 py-3"><div className="flex gap-3"><button type="button" onClick={() => openReject(reject)} className="text-xs font-semibold text-emerald-800">Update</button><button type="button" onClick={() => deleteReject(reject)} className="text-xs font-semibold text-rose-700">Delete</button></div></td><td className="px-3 py-3">{reject.event_date}</td><td className="px-3 py-3">{reject.lot_no || "—"}</td><td className="px-3 py-3">{reject.reject_qty}</td><td className="px-3 py-3">{money(reject.reject_tk)}</td><td className="px-3 py-3">{reject.remarks || "—"}</td></tr>)}{!rejections.length && <TableEmpty columns={6}>No rejected products recorded.</TableEmpty>}</tbody></table></div>
        </section>
      </>}
      {!selectedOperator && <div className="border-y border-gray-200 py-10 text-center text-sm text-gray-500">Select an operator to view production, reject, and payment history.</div>}
    </section>

    {modal === "operator" && <Modal title={editingOperator ? "Update Operator" : "Add Operator"} onClose={closeModal}><form onSubmit={submitOperator} className="grid gap-4 p-5"><Field label="Operator Name"><input required autoFocus maxLength="180" className={inputClass} value={operatorForm.name} onChange={(event) => setOperatorForm({ ...operatorForm, name: event.target.value })} /></Field><Field label="NID Number (Optional)"><input maxLength="30" className={inputClass} value={operatorForm.nid_number} onChange={(event) => setOperatorForm({ ...operatorForm, nid_number: event.target.value })} /></Field><div className="flex justify-end gap-2"><button type="button" onClick={closeModal} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : "Save Operator"}</button></div></form></Modal>}

    {modal === "lot" && <Modal title={editingLot ? "Update Lot" : "Create Lot"} onClose={closeModal}><form onSubmit={submitLot} className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Swing Operator Name">{editingLot ? <input readOnly className={`${inputClass} bg-gray-50`} value={lotOperatorSearch} /> : <><input required list="swing-lot-operators" autoComplete="off" className={inputClass} placeholder="Search active operators" value={lotOperatorSearch} onChange={(event) => { setLotOperatorSearch(event.target.value); const operator = activeOperators.find((row) => row.name.toLowerCase() === event.target.value.toLowerCase()); setLotForm({ ...lotForm, operator: operator ? String(operator.id) : "" }); }} /><datalist id="swing-lot-operators">{lotOperators.map((operator) => <option key={operator.id} value={operator.name} />)}</datalist></>}</Field><Field label="Lot Number (Optional)"><input maxLength="80" className={inputClass} value={lotForm.lot_number} onChange={(event) => setLotForm({ ...lotForm, lot_number: event.target.value })} /></Field><Field label="Lot Product Quantity (Optional)"><input type="number" min="0" step="1" className={inputClass} value={lotForm.quantity} onChange={(event) => setLotForm({ ...lotForm, quantity: event.target.value })} /></Field><Field label="Lot Rate (Optional)"><input type="number" min="0" step="0.01" className={inputClass} value={lotForm.rate} onChange={(event) => setLotForm({ ...lotForm, rate: event.target.value })} /></Field><Field label="Fabrics Specification"><input maxLength="180" className={inputClass} value={lotForm.fabric_specification} onChange={(event) => setLotForm({ ...lotForm, fabric_specification: event.target.value })} /></Field><Field label="Cutting Master Name"><input maxLength="180" className={inputClass} value={lotForm.cutting_master_name} onChange={(event) => setLotForm({ ...lotForm, cutting_master_name: event.target.value })} /></Field><Field label="Lot Creation Date"><input required type="date" className={inputClass} value={lotForm.lot_date} onChange={(event) => setLotForm({ ...lotForm, lot_date: event.target.value })} /></Field><div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={closeModal} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving || !lotForm.operator} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : editingLot ? "Save Lot Changes" : "Create Lot"}</button></div></form></Modal>}

    {modal === "payment" && <Modal title={editingPayment ? "Update Payment" : "Record Payment"} onClose={closeModal}><form onSubmit={submitPayment} className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Selected Operator"><input readOnly className={`${inputClass} bg-gray-50`} value={currentOperatorName} /></Field><Field label="Payment Date"><input required type="date" className={inputClass} value={paymentForm.payment_date} onChange={(event) => setPaymentForm({ ...paymentForm, payment_date: event.target.value })} /></Field><Field label="Payment Amount"><input required min="0.01" step="0.01" type="number" className={inputClass} value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} /></Field><Field label="Remarks (Optional)"><input maxLength="240" className={inputClass} value={paymentForm.remarks} onChange={(event) => setPaymentForm({ ...paymentForm, remarks: event.target.value })} /></Field><div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={closeModal} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : "Save Payment"}</button></div></form></Modal>}

    {modal === "reject" && <Modal title={editingReject ? "Update Reject Details" : "Reject Details"} onClose={closeModal}><form onSubmit={submitReject} className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Selected Operator"><input readOnly className={`${inputClass} bg-gray-50`} value={currentOperatorName} /></Field><Field label="Search Lot Number"><input required autoComplete="off" className={inputClass} placeholder="Search this operator's lots" value={lotSearch} onFocus={() => setLotPickerOpen(true)} onChange={(event) => { setLotSearch(event.target.value); setLotPickerOpen(true); const lot = lots.find((row) => (row.lot_number || `Lot ${row.id}`) === event.target.value); setRejectForm({ ...rejectForm, lot: lot ? String(lot.id) : "" }); }} />{lotPickerOpen && <ul className="mt-1 max-h-40 overflow-auto rounded-lg border border-gray-200 bg-white">{visibleLots.map((lot) => <li key={lot.id}><button type="button" onClick={() => { setLotSearch(lot.lot_number || `Lot ${lot.id}`); setRejectForm({ ...rejectForm, lot: String(lot.id) }); setLotPickerOpen(false); }} className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-emerald-50"><span>{lot.lot_number || `Lot ${lot.id}`} · {lot.quantity} assigned</span><span className="whitespace-nowrap text-gray-500">{lot.available_quantity} available</span></button></li>)}{!visibleLots.length && <li className="px-3 py-2 text-xs text-gray-500">No matching lots</li>}</ul>}</Field><Field label="Reject Quantity"><input required min="1" max={availableForReject || undefined} step="1" type="number" className={inputClass} value={rejectForm.quantity} onChange={(event) => setRejectForm({ ...rejectForm, quantity: event.target.value })} /></Field><Field label="Available Quantity"><input readOnly className={`${inputClass} bg-gray-50`} value={selectedLot ? `${availableForReject} pcs` : "Select a lot"} /></Field><Field label="Reject Date"><input required type="date" min={selectedLot?.lot_date} className={inputClass} value={rejectForm.reject_date} onChange={(event) => setRejectForm({ ...rejectForm, reject_date: event.target.value })} /></Field><Field label="Calculated Reject Amount"><input readOnly className={`${inputClass} bg-gray-50`} value={money(rejectAmount)} /></Field><Field label="Remarks (Optional)"><input maxLength="240" className={inputClass} value={rejectForm.remarks} onChange={(event) => setRejectForm({ ...rejectForm, remarks: event.target.value })} /></Field><div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={closeModal} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving || !selectedLot || Number(rejectForm.quantity) > availableForReject} className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : "Save Reject"}</button></div></form></Modal>}
  </div>;

  function summaryValue(key) {
    return Number(statementData?.summary?.[key] || 0).toLocaleString();
  }
}
