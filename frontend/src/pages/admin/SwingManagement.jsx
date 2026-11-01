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

function Field({ label, children, className = "" }) {
  return <label className={`block text-xs font-medium text-gray-600 ${className}`}>{label}{children}</label>;
}

function Metric({ label, value, currency = false, accent = "emerald" }) {
  const colors = {
    emerald: "border-emerald-700",
    amber: "border-amber-600",
    sky: "border-sky-600",
    rose: "border-rose-600",
  };
  return <div className={`border-l-2 ${colors[accent]} py-1 pl-3`}>
    <p className="text-[11px] font-semibold uppercase text-gray-500">{label}</p>
    <p className="mt-1 text-base font-semibold text-gray-900">{currency ? money(value) : Number(value || 0).toLocaleString()}</p>
  </div>;
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

export default function SwingManagement() {
  const [operators, setOperators] = useState([]);
  const [operatorSearch, setOperatorSearch] = useState("");
  const [selectedOperator, setSelectedOperator] = useState("");
  const [statementData, setStatementData] = useState(null);
  const [operatorForm, setOperatorForm] = useState(blankOperator);
  const [editingOperator, setEditingOperator] = useState(null);
  const [lotForm, setLotForm] = useState(blankLot);
  const [editingLot, setEditingLot] = useState(null);
  const [lotSearch, setLotSearch] = useState("");
  const [paymentForm, setPaymentForm] = useState(blankPayment);
  const [editingPayment, setEditingPayment] = useState(null);
  const [rejectForm, setRejectForm] = useState(blankReject);
  const [editingReject, setEditingReject] = useState(null);
  const [lotPickerOpen, setLotPickerOpen] = useState(false);
  const [modal, setModal] = useState("");
  const [status, setStatus] = useState({ loading: true, saving: false, error: "", message: "" });

  const activeOperators = useMemo(() => operators.filter((operator) => operator.is_active), [operators]);
  const shownOperators = useMemo(() => operators.filter((operator) => operator.name.toLowerCase().includes(operatorSearch.toLowerCase())), [operators, operatorSearch]);
  const selected = statementData?.operator;
  const lots = statementData?.lots || [];
  const summary = statementData?.summary;
  const selectedLot = lots.find((lot) => String(lot.id) === String(rejectForm.lot));
  const editedReject = statementData?.statement.find((row) => row.event_type === "reject" && row.event_id === editingReject);
  const rejectAvailable = selectedLot
    ? selectedLot.available_quantity + (editedReject?.lot_id === selectedLot.id ? editedReject.reject_qty : 0)
    : 0;

  async function loadOperators() {
    const response = await swingApi.operators.list();
    setOperators(rowsOf(response));
  }

  async function loadStatement(operatorId = selectedOperator) {
    if (!operatorId) {
      setStatementData(null);
      return;
    }
    const response = await swingApi.operators.statement(operatorId);
    setStatementData(response.data);
  }

  useEffect(() => {
    loadOperators()
      .then((response) => setStatus((current) => ({ ...current, loading: false })))
      .catch((error) => setStatus((current) => ({ ...current, loading: false, error: errorText(error) })));
  }, []);

  useEffect(() => {
    if (!selectedOperator) {
      setStatementData(null);
      setLotForm((current) => ({ ...current, operator: "" }));
      return;
    }
    setLotForm((current) => ({ ...current, operator: selectedOperator }));
    setStatus((current) => ({ ...current, loading: true, error: "" }));
    loadStatement(selectedOperator)
      .catch((error) => setStatus((current) => ({ ...current, error: errorText(error) })))
      .finally(() => setStatus((current) => ({ ...current, loading: false })));
  }, [selectedOperator]);

  function notifyError(error) {
    setStatus((current) => ({ ...current, error: errorText(error), message: "" }));
  }

  async function submitOperator(event) {
    event.preventDefault();
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      if (editingOperator) {
        await swingApi.operators.update(editingOperator, operatorForm);
        setStatus((current) => ({ ...current, message: "Operator details updated." }));
      } else {
        const response = await swingApi.operators.create(operatorForm);
        setSelectedOperator(String(response.data.id));
        setStatus((current) => ({ ...current, message: "Swing operator added." }));
      }
      setOperatorForm(blankOperator);
      setEditingOperator(null);
      await loadOperators();
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  function editOperator(operator) {
    setEditingOperator(operator.id);
    setOperatorForm({ name: operator.name, nid_number: operator.nid_number || "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function deleteOperator(operator) {
    if (!window.confirm(`Deactivate ${operator.name}? Their lots and payment history will be preserved.`)) return;
    try {
      await swingApi.operators.delete(operator.id);
      await loadOperators();
      setStatus((current) => ({ ...current, message: `${operator.name} was deactivated; history was preserved.`, error: "" }));
    } catch (error) { notifyError(error); }
  }

  async function submitLot(event) {
    event.preventDefault();
    if (!selectedOperator) return;
    setStatus((current) => ({ ...current, saving: true, error: "", message: "" }));
    try {
      const payload = { ...lotForm, operator: Number(selectedOperator), quantity: Number(lotForm.quantity || 0), rate: lotForm.rate || "0" };
      if (editingLot) await swingApi.lots.update(editingLot, payload);
      else await swingApi.lots.create(payload);
      setLotForm({ ...blankLot, operator: selectedOperator, lot_date: today });
      setEditingLot(null);
      await loadStatement();
      setStatus((current) => ({ ...current, message: editingLot ? "Lot updated; balances recalculated." : "Production lot created." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  function editLot(lot) {
    setEditingLot(lot.id);
    setLotForm({ operator: selectedOperator, lot_number: lot.lot_number, quantity: String(lot.quantity), fabric_specification: lot.fabric_specification, rate: String(lot.rate), cutting_master_name: lot.cutting_master_name, lot_date: lot.lot_date });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function deleteLot(lot) {
    if (!window.confirm(`Delete lot ${lot.lot_number || `#${lot.id}`} from active records? Related reject history is retained.`)) return;
    try {
      await swingApi.lots.delete(lot.id);
      await loadStatement();
      setStatus((current) => ({ ...current, message: "Lot deactivated and statement recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  function openPayment(payment = null) {
    setEditingPayment(payment?.id || null);
    setPaymentForm(payment ? { payment_date: payment.event_date, amount: String(payment.receive_tk), remarks: payment.remarks || "" } : { ...blankPayment, payment_date: today });
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
      await loadStatement();
      setStatus((current) => ({ ...current, message: "Payment saved; operator balance recalculated." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deletePayment(event) {
    if (!window.confirm("Delete this payment from active records? Its history will be retained.")) return;
    try {
      await swingApi.payments.delete(event.payment_id);
      await loadStatement();
      setStatus((current) => ({ ...current, message: "Payment deactivated and balance recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  function openReject(reject = null) {
    setEditingReject(reject?.id || null);
    setRejectForm(reject
      ? { lot: String(reject.lot_id), quantity: String(reject.reject_qty), reject_date: reject.event_date, remarks: reject.remarks || "" }
      : { ...blankReject, reject_date: today });
    setLotSearch(reject ? (lots.find((lot) => String(lot.id) === String(reject.lot_id))?.lot_number || "") : "");
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
      await loadStatement();
      setStatus((current) => ({ ...current, message: "Reject details saved; balances recalculated." }));
    } catch (error) { notifyError(error); }
    finally { setStatus((current) => ({ ...current, saving: false })); }
  }

  async function deleteReject(event) {
    if (!window.confirm("Delete this rejection from active records? Its history will be retained.")) return;
    try {
      await swingApi.rejects.delete(event.reject_id);
      await loadStatement();
      setStatus((current) => ({ ...current, message: "Rejection deactivated and balance recalculated.", error: "" }));
    } catch (error) { notifyError(error); }
  }

  const filteredLots = lots.filter((lot) => (lot.lot_number || `Lot ${lot.id}`).toLowerCase().includes(lotSearch.toLowerCase()));
  const rejectionAmount = selectedLot ? Number(rejectForm.quantity || 0) * Number(selectedLot.rate) : 0;

  return <div className="space-y-6">
    <header className="dashboard-heading">
      <div><p className="dashboard-eyebrow">Production payroll</p><h1>Swing Management</h1><p className="mt-1 text-sm text-gray-600">Operators, sewing lots, rejects, payments, and running balances.</p></div>
    </header>
    {(status.error || status.message) && <div role={status.error ? "alert" : "status"} className={`whitespace-pre-line rounded-lg border p-3 text-sm ${status.error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{status.error || status.message}</div>}

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>{editingOperator ? "Update swing operator" : "Add swing operator"}</h2><p>Operator records and historical production are kept separate from employee payroll.</p></div></div>
      <form onSubmit={submitOperator} className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
        <Field label="Operator name"><input required maxLength="180" className={inputClass} value={operatorForm.name} onChange={(event) => setOperatorForm({ ...operatorForm, name: event.target.value })} /></Field>
        <Field label="NID number (optional)"><input maxLength="30" className={inputClass} value={operatorForm.nid_number} onChange={(event) => setOperatorForm({ ...operatorForm, nid_number: event.target.value })} /></Field>
        <div className="flex items-end gap-2"><button disabled={status.saving} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : editingOperator ? "Update operator" : "Add operator"}</button>{editingOperator && <button type="button" onClick={() => { setEditingOperator(null); setOperatorForm(blankOperator); }} className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm">Cancel</button>}</div>
      </form>
      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(220px,0.65fr)_minmax(0,1.35fr)]">
        <Field label="Search operators"><input className={inputClass} placeholder="Type operator name" value={operatorSearch} onChange={(event) => setOperatorSearch(event.target.value)} /></Field>
        <div className="overflow-x-auto"><table className="w-full min-w-[480px] text-left text-sm"><thead className="text-xs uppercase text-gray-500"><tr><th className="px-3 py-2">Operator</th><th className="px-3 py-2">NID</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Actions</th></tr></thead><tbody className="divide-y divide-gray-100">
          {shownOperators.map((operator) => <tr key={operator.id} className={String(operator.id) === selectedOperator ? "bg-emerald-50/60" : ""}><td className="px-3 py-2.5"><button type="button" onClick={() => setSelectedOperator(String(operator.id))} className="font-medium text-emerald-800 hover:underline">{operator.name}</button></td><td className="px-3 py-2.5">{operator.nid_number || "—"}</td><td className="px-3 py-2.5">{operator.is_active ? "Active" : "Inactive"}</td><td className="px-3 py-2.5"><div className="flex gap-2"><button type="button" onClick={() => editOperator(operator)} className="text-xs font-semibold text-gray-700 hover:text-emerald-800">Edit</button>{operator.is_active && <button type="button" onClick={() => deleteOperator(operator)} className="text-xs font-semibold text-rose-700">Deactivate</button>}</div></td></tr>)}
          {!shownOperators.length && <tr><td colSpan="4" className="px-3 py-5 text-center text-gray-500">{status.loading ? "Loading operators…" : "No operators found."}</td></tr>}
        </tbody></table></div>
      </div>
    </section>

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>Create lot</h2><p>Assign a dated production lot to an active swing operator.</p></div></div>
      {!activeOperators.length ? <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">Add an active swing operator before creating a lot.</p> : <form onSubmit={submitLot} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Field label="Swing operator"><input list="swing-active-operators" required className={inputClass} value={activeOperators.find((operator) => String(operator.id) === lotForm.operator)?.name || ""} onChange={(event) => { const operator = activeOperators.find((row) => row.name === event.target.value); setLotForm({ ...lotForm, operator: operator ? String(operator.id) : "" }); if (operator) setSelectedOperator(String(operator.id)); }} placeholder="Type to search operators" /><datalist id="swing-active-operators">{activeOperators.map((operator) => <option key={operator.id} value={operator.name} />)}</datalist></Field>
        <Field label="Lot number"><input className={inputClass} maxLength="80" value={lotForm.lot_number} onChange={(event) => setLotForm({ ...lotForm, lot_number: event.target.value })} /></Field>
        <Field label="Product quantity"><input className={inputClass} type="number" min="0" step="1" value={lotForm.quantity} onChange={(event) => setLotForm({ ...lotForm, quantity: event.target.value })} /></Field>
        <Field label="Lot rate per product"><input className={inputClass} type="number" min="0" step="0.01" value={lotForm.rate} onChange={(event) => setLotForm({ ...lotForm, rate: event.target.value })} /></Field>
        <Field label="Fabrics specification / colour"><input className={inputClass} maxLength="180" value={lotForm.fabric_specification} onChange={(event) => setLotForm({ ...lotForm, fabric_specification: event.target.value })} /></Field>
        <Field label="Cutting master name"><input className={inputClass} maxLength="180" value={lotForm.cutting_master_name} onChange={(event) => setLotForm({ ...lotForm, cutting_master_name: event.target.value })} /></Field>
        <Field label="Lot creation date"><input required type="date" className={inputClass} value={lotForm.lot_date} onChange={(event) => setLotForm({ ...lotForm, lot_date: event.target.value })} /></Field>
        <div className="flex items-end gap-2"><button disabled={status.saving || !lotForm.operator} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : editingLot ? "Update lot" : "Create lot"}</button>{editingLot && <button type="button" onClick={() => { setEditingLot(null); setLotForm({ ...blankLot, operator: selectedOperator, lot_date: today }); }} className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm">Cancel</button>}</div>
      </form>}
    </section>

    {selectedOperator && <>
      <section className="space-y-4">
        <div className="dashboard-section-heading"><div><h2>{selected?.name || "Swing operator details"}</h2><p>Production and financial statement · balances recalculate from dated transactions.</p></div><div className="flex flex-wrap gap-2"><button type="button" onClick={() => openPayment()} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">Payment</button><button type="button" onClick={() => openReject()} disabled={!lots.length} className="rounded-lg border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-800 disabled:opacity-50">Reject details</button></div></div>
        {summary && <div className="grid grid-cols-2 gap-4 border-y border-gray-200 py-4 sm:grid-cols-3 xl:grid-cols-7">
          <Metric label="Total lots" value={summary.total_lots} currency={false} />
          <Metric label="Products assigned" value={summary.total_products_assigned} currency={false} accent="sky" />
          <Metric label="Rejected quantity" value={summary.total_rejected_quantity} currency={false} accent="rose" />
          <Metric label="Accepted quantity" value={summary.total_accepted_quantity} currency={false} accent="emerald" />
          <Metric label="Net sewing amount" value={summary.total_sewing_amount} accent="amber" />
          <Metric label="Payments received" value={summary.total_payments_received} accent="sky" />
          <Metric label="Outstanding balance" value={summary.current_outstanding_balance} accent="rose" />
        </div>}
        <div className="overflow-x-auto border-y border-gray-200">
          <table className="min-w-[1550px] w-full text-left text-sm"><thead className="bg-gray-50 text-[11px] uppercase text-gray-600"><tr>{["Date / Type", "B/F Taka", "Colour", "Lot No", "Lot QTY", "Lot Rate", "Total Tk", "Reject QTY", "Reject Tk", "Receive Tk", "Due Taka", "Remarks", "Actions"].map((heading) => <th key={heading} className="whitespace-nowrap px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">
            {statementData?.statement.map((row) => <tr key={`${row.event_type}-${row.event_id}`} className={row.event_type === "payment" ? "bg-sky-50/30" : row.event_type === "reject" ? "bg-rose-50/30" : ""}>
              <td className="whitespace-nowrap px-3 py-3">{row.event_date}<span className="ml-2 text-[10px] font-semibold uppercase text-gray-500">{row.event_type}</span></td><td className="px-3 py-3">{money(row.bf_taka)}</td><td className="px-3 py-3">{row.colour || "—"}</td><td className="px-3 py-3">{row.lot_no || "—"}</td><td className="px-3 py-3">{row.lot_qty ?? "—"}</td><td className="px-3 py-3">{row.lot_qty !== null ? money(row.lot_rate) : "—"}</td><td className="px-3 py-3">{Number(row.total_tk) ? money(row.total_tk) : "—"}</td><td className="px-3 py-3">{row.reject_qty || "—"}</td><td className="px-3 py-3">{Number(row.reject_tk) ? money(row.reject_tk) : "—"}</td><td className="px-3 py-3">{Number(row.receive_tk) ? money(row.receive_tk) : "—"}</td><td className="px-3 py-3 font-semibold">{money(row.due_taka)}</td><td className="px-3 py-3">{row.remarks || "—"}</td><td className="px-3 py-3"><div className="flex gap-2">{row.event_type === "lot" && <><button type="button" onClick={() => editLot(lots.find((lot) => lot.id === row.lot_id))} className="text-xs font-semibold text-emerald-800">Edit</button><button type="button" onClick={() => deleteLot(lots.find((lot) => lot.id === row.lot_id))} className="text-xs font-semibold text-rose-700">Delete</button></>}{row.event_type === "payment" && <><button type="button" onClick={() => openPayment(row)} className="text-xs font-semibold text-emerald-800">Edit</button><button type="button" onClick={() => deletePayment(row)} className="text-xs font-semibold text-rose-700">Delete</button></>}{row.event_type === "reject" && <><button type="button" onClick={() => openReject(row)} className="text-xs font-semibold text-emerald-800">Edit</button><button type="button" onClick={() => deleteReject(row)} className="text-xs font-semibold text-rose-700">Delete</button></>}</div></td>
            </tr>)}
            {!status.loading && !statementData?.statement.length && <tr><td colSpan="13" className="px-3 py-8 text-center text-gray-500">No production, rejection, or payment transactions for this operator.</td></tr>}
            {status.loading && <tr><td colSpan="13" className="px-3 py-8 text-center text-gray-500">Loading operator statement…</td></tr>}
          </tbody></table>
        </div>
      </section>
      <section className="dashboard-chart-panel">
        <div className="dashboard-section-heading mb-3"><div><h2>Lot records</h2><p>Available quantity is assigned quantity less active rejects.</p></div></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="text-xs uppercase text-gray-500"><tr>{["Date", "Lot number", "Colour", "Quantity", "Rejected", "Available", "Rate", "Actions"].map((heading) => <th key={heading} className="px-3 py-2">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">{lots.map((lot) => <tr key={lot.id}><td className="px-3 py-3">{lot.lot_date}</td><td className="px-3 py-3">{lot.lot_number || "—"}</td><td className="px-3 py-3">{lot.fabric_specification || "—"}</td><td className="px-3 py-3">{lot.quantity}</td><td className="px-3 py-3">{lot.rejected_quantity}</td><td className="px-3 py-3">{lot.available_quantity}</td><td className="px-3 py-3">{money(lot.rate)}</td><td className="px-3 py-3"><div className="flex gap-3"><button type="button" onClick={() => editLot(lot)} className="text-xs font-semibold text-emerald-800">Edit</button><button type="button" onClick={() => deleteLot(lot)} className="text-xs font-semibold text-rose-700">Delete</button></div></td></tr>)}{!lots.length && <tr><td colSpan="8" className="px-3 py-5 text-center text-gray-500">No lots created for this operator.</td></tr>}</tbody></table></div>
      </section>
    </>}

    {modal === "payment" && <Modal title={editingPayment ? "Update payment" : "Record payment"} onClose={() => !status.saving && setModal("")}><form onSubmit={submitPayment} className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Swing operator"><input readOnly className={`${inputClass} bg-gray-50`} value={selected?.name || ""} /></Field><Field label="Payment date"><input required type="date" className={inputClass} value={paymentForm.payment_date} onChange={(event) => setPaymentForm({ ...paymentForm, payment_date: event.target.value })} /></Field><Field label="Payment amount"><input required min="0.01" step="0.01" type="number" className={inputClass} value={paymentForm.amount} onChange={(event) => setPaymentForm({ ...paymentForm, amount: event.target.value })} /></Field><Field label="Remarks (optional)"><input maxLength="240" className={inputClass} value={paymentForm.remarks} onChange={(event) => setPaymentForm({ ...paymentForm, remarks: event.target.value })} /></Field><div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={() => setModal("")} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : "Save payment"}</button></div></form></Modal>}

    {modal === "reject" && <Modal title={editingReject ? "Update reject details" : "Record rejected products"} onClose={() => !status.saving && setModal("")}><form onSubmit={submitReject} className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Swing operator"><input readOnly className={`${inputClass} bg-gray-50`} value={selected?.name || ""} /></Field><Field label="Lot number"><input required autoComplete="off" className={inputClass} placeholder="Search this operator's lots" value={lotSearch} onFocus={() => setLotPickerOpen(true)} onChange={(event) => { setLotSearch(event.target.value); setLotPickerOpen(true); const lot = lots.find((row) => (row.lot_number || `Lot ${row.id}`) === event.target.value); setRejectForm({ ...rejectForm, lot: lot ? String(lot.id) : "" }); }} /><span className="mt-1 block text-[11px] text-gray-500">Choose the lot below; other operators’ lots are not shown.</span>{lotPickerOpen && <ul className="mt-1 max-h-40 overflow-auto rounded-lg border border-gray-200 bg-white">{filteredLots.map((lot) => <li key={lot.id}><button type="button" onClick={() => { setLotSearch(lot.lot_number || `Lot ${lot.id}`); setRejectForm({ ...rejectForm, lot: String(lot.id) }); setLotPickerOpen(false); }} className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs hover:bg-emerald-50"><span className="font-semibold text-gray-800">{lot.lot_number || `Lot ${lot.id}`} · {lot.quantity} assigned</span><span className="whitespace-nowrap text-gray-500">{lot.available_quantity} available · {money(lot.rate)}/pc</span></button></li>)}{!filteredLots.length && <li className="px-3 py-2 text-xs text-gray-500">No matching lots</li>}</ul>}</Field><Field label="Available quantity"><input readOnly className={`${inputClass} bg-gray-50`} value={selectedLot ? `${rejectAvailable} pcs` : "Select a lot"} /></Field><Field label="Reject quantity"><input required min="1" max={rejectAvailable || undefined} step="1" type="number" className={inputClass} value={rejectForm.quantity} onChange={(event) => setRejectForm({ ...rejectForm, quantity: event.target.value })} /></Field><Field label="Reject date"><input required type="date" min={selectedLot?.lot_date} className={inputClass} value={rejectForm.reject_date} onChange={(event) => setRejectForm({ ...rejectForm, reject_date: event.target.value })} /></Field><Field label="Calculated reject amount"><input readOnly className={`${inputClass} bg-gray-50`} value={money(rejectionAmount)} /></Field><Field label="Remarks (optional)" className="sm:col-span-2"><input maxLength="240" className={inputClass} value={rejectForm.remarks} onChange={(event) => setRejectForm({ ...rejectForm, remarks: event.target.value })} /></Field><div className="flex justify-end gap-2 sm:col-span-2"><button type="button" onClick={() => setModal("")} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button><button disabled={status.saving || !selectedLot || Number(rejectForm.quantity) > rejectAvailable} className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{status.saving ? "Saving…" : "Save reject"}</button></div></form></Modal>}
  </div>;
}
