import { useEffect, useState } from "react";
import { employeeApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

const monthNow = () => localDateString().slice(0, 7);
const fieldClass = "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-emerald-500";
const money = (value) => `৳ ${Number(value || 0).toLocaleString("en-BD", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const apiErrorMessage = (error, fallback) => {
  const payload = error.response?.data;
  const details = payload?.errors ?? payload;
  const fieldError = details && typeof details === "object"
    ? Object.values(details).flat().find((message) => typeof message === "string")
    : null;
  return fieldError || payload?.detail || fallback;
};
const newEmployee = () => ({ name: "", employee_id: "", nid_number: "", designation: "", salary: "" });

function payrollPreview(entry) {
  return Number(entry.base_salary || 0)
    - Number(entry.absence_amount || 0)
    - Number(entry.leave_amount || 0)
    + Number(entry.overtime_hours || 0) * Number(entry.overtime_rate || 0)
    + Number(entry.attendance_bonus || 0)
    - Number(entry.advance_deduction || 0)
    - Number(entry.loan || 0)
    - Number(entry.other_deduction || 0);
}

export default function EmployeeManagement() {
  const [employees, setEmployees] = useState([]);
  const [entries, setEntries] = useState([]);
  const [history, setHistory] = useState([]);
  const [month, setMonth] = useState(monthNow);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(newEmployee);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [employeeEdit, setEmployeeEdit] = useState(newEmployee);
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [employeesLoading, setEmployeesLoading] = useState(true);
  const [employeesLoadError, setEmployeesLoadError] = useState("");
  const [sheetLoading, setSheetLoading] = useState(true);
  const [sheetLoadError, setSheetLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadEmployees(query = search) {
    const response = await employeeApi.list(query);
    const rows = response.data.results ?? response.data;
    if (!Array.isArray(rows)) throw new Error("Invalid employee response.");
    setEmployees(rows);
    setEmployeesLoadError("");
  }

  async function refreshEmployees(query = search) {
    setEmployeesLoading(true);
    setEmployeesLoadError("");
    try { await loadEmployees(query); }
    catch (err) { setEmployeesLoadError(apiErrorMessage(err, "Could not load employees.")); }
    finally { setEmployeesLoading(false); }
  }

  async function loadSheet(selectedMonth = month) {
    const response = await employeeApi.salaryEntries(selectedMonth);
    const rows = response.data.results ?? response.data;
    if (!Array.isArray(rows)) throw new Error("Invalid salary sheet response.");
    setEntries(rows);
    setSheetLoadError("");
  }

  async function loadHistory() {
    const response = await employeeApi.salarySheets();
    setHistory(response.data);
  }

  useEffect(() => {
    const timer = window.setTimeout(() => refreshEmployees(search), 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let mounted = true;
    setSheetLoading(true);
    setSheetLoadError("");
    employeeApi.salaryEntries(month)
      .then(({ data }) => {
        const rows = data.results ?? data;
        if (!Array.isArray(rows)) throw new Error("Invalid salary sheet response.");
        if (mounted) setEntries(rows);
      })
      .catch((err) => {
        if (mounted) {
          setEntries([]);
          setSheetLoadError(apiErrorMessage(err, "Could not load the salary sheet."));
        }
      })
      .finally(() => { if (mounted) setSheetLoading(false); });
    return () => { mounted = false; };
  }, [month]);

  useEffect(() => {
    loadHistory().catch((err) => setError(apiErrorMessage(err, "Could not load salary history.")));
  }, []);

  async function addEmployee(event) {
    event.preventDefault();
    setBusy(true); setError(""); setMessage("");
    try {
      await employeeApi.create({ ...form, salary: Number(form.salary), nid_number: form.nid_number || null });
      setForm(newEmployee());
      await refreshEmployees();
      setMessage("Employee added successfully.");
    } catch (err) { setError(apiErrorMessage(err, "Could not add employee. Check the fields and employee ID.")); }
    finally { setBusy(false); }
  }

  async function createSheet() {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await employeeApi.createSalarySheet(month);
      const rows = response.data.results ?? response.data;
      setEntries(rows);
      await loadHistory();
      setMessage(`Salary sheet ready for ${month}.`);
    } catch (err) { setError(apiErrorMessage(err, "Could not create or open the salary sheet.")); }
    finally { setBusy(false); }
  }

  function editEntry(id, key, value) {
    setEntries((current) => current.map((entry) => {
      if (entry.id !== id) return entry;
      const updated = { ...entry, [key]: value };
      if (key === "absent_days") {
        const perDay = Number(entry.base_salary || 0) / Number(entry.total_days || 1);
        updated.absence_amount = (perDay * Number(value || 0)).toFixed(2);
      }
      return updated;
    }));
  }

  async function saveEntry(entry) {
    setBusy(true); setError("");
    try {
      const response = await employeeApi.updateSalaryEntry(entry.id, {
        absent_days: Number(entry.absent_days), leave_days: Number(entry.leave_days),
        leave_amount: Number(entry.leave_amount), absence_amount: Number(entry.absence_amount),
        overtime_hours: Number(entry.overtime_hours), overtime_rate: Number(entry.overtime_rate),
        attendance_bonus: Number(entry.attendance_bonus), advance_balance: Number(entry.advance_balance),
        advance_deduction: Number(entry.advance_deduction), outstanding_loan: Number(entry.outstanding_loan),
        loan: Number(entry.loan), other_deduction: Number(entry.other_deduction),
      });
      setEntries((current) => current.map((row) => row.id === entry.id ? response.data : row));
      setEditingEntryId(null);
      setMessage(`${entry.employee_name}'s salary updated.`);
    } catch (err) { setError(apiErrorMessage(err, "Could not update salary. Check the entered values.")); }
    finally { setBusy(false); }
  }

  function beginEmployeeEdit(employee) {
    setEditingEmployee(employee.id);
    setEmployeeEdit({
      name: employee.name,
      employee_id: employee.employee_id,
      nid_number: employee.nid_number || "",
      designation: employee.designation,
      salary: employee.salary,
    });
  }

  async function saveEmployeeEdit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await employeeApi.update(editingEmployee, { ...employeeEdit, salary: Number(employeeEdit.salary), nid_number: employeeEdit.nid_number || null });
      setEditingEmployee(null);
      await refreshEmployees();
      setMessage("Employee details updated.");
    } catch (err) { setError(apiErrorMessage(err, "Could not update employee details.")); }
    finally { setBusy(false); }
  }

  async function deleteEmployee(employee) {
    if (!window.confirm(`Remove ${employee.name} (${employee.employee_id}) from active employees? Salary history will be preserved.`)) return;
    setBusy(true); setError("");
    try {
      await employeeApi.delete(employee.id);
      await refreshEmployees();
      setMessage(`${employee.name} removed from active employees; salary history was preserved.`);
    } catch (err) { setError(apiErrorMessage(err, "Could not delete employee.")); }
    finally { setBusy(false); }
  }

  async function deleteEntry(entry) {
    if (!window.confirm(`Remove ${entry.employee_name}'s salary row from ${month}? Other months and employee profile will remain.`)) return;
    setBusy(true); setError("");
    try {
      await employeeApi.deleteSalaryEntry(entry.id);
      setEntries((current) => current.filter((row) => row.id !== entry.id));
      await loadHistory();
      setMessage(`${entry.employee_name}'s ${month} salary row was removed.`);
    } catch (err) { setError(apiErrorMessage(err, "Could not remove this salary row.")); }
    finally { setBusy(false); }
  }

  const totals = entries.reduce((result, entry) => {
    result.basic += Number(entry.base_salary || 0);
    result.overtime += Number(entry.overtime_pay || (Number(entry.overtime_hours || 0) * Number(entry.overtime_rate || 0)));
    result.bonuses += Number(entry.attendance_bonus || 0) + Math.max(-Number(entry.leave_amount || 0), 0);
    result.deductions += Number(entry.absence_amount || 0)
      + Math.max(Number(entry.leave_amount || 0), 0)
      + Number(entry.advance_deduction || 0)
      + Number(entry.loan || 0)
      + Number(entry.other_deduction || 0);
    result.payable += payrollPreview(entry);
    return result;
  }, { basic: 0, overtime: 0, bonuses: 0, deductions: 0, payable: 0 });

  const employeeForm = (values, setValues, onSubmit, editing = false) => (
    <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <input className={fieldClass} placeholder="Employee name" aria-label="Employee name" required maxLength="180" value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} />
      <input className={fieldClass} placeholder="Employee ID" aria-label="Employee ID" required maxLength="80" value={values.employee_id} onChange={(event) => setValues({ ...values, employee_id: event.target.value })} />
      <input className={fieldClass} placeholder="NID number (optional)" aria-label="NID number" maxLength="30" value={values.nid_number} onChange={(event) => setValues({ ...values, nid_number: event.target.value })} />
      <input className={fieldClass} placeholder="Designation" aria-label="Designation" required maxLength="120" value={values.designation} onChange={(event) => setValues({ ...values, designation: event.target.value })} />
      <input className={fieldClass} type="number" min="0" step="0.01" placeholder="Monthly basic salary" aria-label="Monthly basic salary" required value={values.salary} onChange={(event) => setValues({ ...values, salary: event.target.value })} />
      <div className="flex gap-2">
        <button disabled={busy} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">{editing ? "Save changes" : "Add employee"}</button>
        {editing && <button type="button" onClick={() => setEditingEmployee(null)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button>}
      </div>
    </form>
  );

  return <div className="space-y-6">
    <header className="dashboard-heading">
      <div><p className="dashboard-eyebrow">Team and payroll</p><h1>Employee Management</h1><p className="mt-1 text-sm text-gray-600">Employee profiles, monthly salary sheets, and payroll history.</p></div>
    </header>
    {(error || message) && <div role={error ? "alert" : "status"} className={`rounded-xl border p-3 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{error || message}</div>}

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>Employee profiles</h2><p>Basic salary and profile details are snapshotted into each monthly sheet.</p></div></div>
      {employeeForm(form, setForm, addEmployee)}
      {editingEmployee && <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4"><h3 className="mb-3 text-sm font-semibold text-emerald-900">Update employee profile</h3>{employeeForm(employeeEdit, setEmployeeEdit, saveEmployeeEdit, true)}</div>}
      <div className="my-4 flex flex-wrap items-center justify-between gap-3">
        <input className={`${fieldClass} max-w-sm`} placeholder="Search name, employee ID, or NID" aria-label="Search employees" value={search} onChange={(event) => setSearch(event.target.value)} />
        <span className="text-sm text-gray-500">{employees.length} active employee{employees.length === 1 ? "" : "s"}</span>
      </div>
      {employeesLoadError && <div role="alert" className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><span>{employeesLoadError}</span><button type="button" onClick={() => refreshEmployees()} disabled={employeesLoading} className="rounded-lg border border-rose-300 px-3 py-1.5 font-semibold disabled:opacity-50">Retry</button></div>}
      <div className="overflow-x-auto"><table className="min-w-[850px] w-full text-left text-sm"><thead className="text-xs uppercase text-gray-500"><tr>{["Employee", "Employee ID", "NID Number", "Designation", "Monthly basic salary", "Actions"].map((heading) => <th key={heading} className="px-3 py-2">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">
        {employees.map((employee) => <tr key={employee.id}><td className="px-3 py-3 font-medium">{employee.name}</td><td className="px-3 py-3">{employee.employee_id}</td><td className="px-3 py-3">{employee.nid_number || "—"}</td><td className="px-3 py-3">{employee.designation}</td><td className="px-3 py-3">{money(employee.salary)}</td><td className="px-3 py-3"><div className="flex gap-2"><button type="button" onClick={() => beginEmployeeEdit(employee)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800">Update</button><button type="button" disabled={busy} onClick={() => deleteEmployee(employee)} className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Delete</button></div></td></tr>)}
        {employeesLoading && <tr><td className="px-3 py-5 text-gray-500" colSpan="6">Loading employees…</td></tr>}
        {!employeesLoading && !employeesLoadError && !employees.length && <tr><td className="px-3 py-5 text-gray-500" colSpan="6">{search ? "No matching employees found." : "No employees added yet."}</td></tr>}
      </tbody></table></div>
    </section>

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>Monthly salary sheet</h2><p>Paid leave is not deducted. Enter leave adjustment as a positive deduction or a negative paid-leave credit.</p></div></div>
      {sheetLoadError && <div role="alert" className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{sheetLoadError}</div>}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium text-gray-600">Salary month<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} className={`${fieldClass} mt-1 block w-auto`} /></label>
        <label className="text-sm font-medium text-gray-600">Salary history<select value="" onChange={(event) => event.target.value && setMonth(event.target.value)} className={`${fieldClass} mt-1 block w-auto`}><option value="">Open a saved month</option>{history.map((sheet) => <option key={sheet.id} value={sheet.month}>{sheet.month} · {sheet.entry_count} rows</option>)}</select></label>
        <button type="button" disabled={busy || employeesLoading || !employees.length} onClick={createSheet} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">Create / open sheet</button>
        <button type="button" disabled={busy || !entries.length} onClick={() => employeeApi.exportSalarySheet(month).catch((err) => setError(apiErrorMessage(err, "Could not download Excel sheet.")))} className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50">Export Excel</button>
      </div>
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        {[["Basic salary", totals.basic], ["Overtime", totals.overtime], ["Bonuses", totals.bonuses], ["Deductions", totals.deductions], ["Total payable", totals.payable]].map(([label, amount]) => <div key={label} className="border-l-2 border-emerald-600 pl-3 py-1"><p className="text-xs uppercase text-gray-500">{label}</p><p className="mt-1 text-sm font-semibold text-gray-900">{money(amount)}</p></div>)}
      </div>
      <div className="overflow-x-auto"><table className="min-w-[2200px] w-full text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr>{["Employee", "Basic / Net", "Per-day rate", "Absent days", "Leave days", "Leave adjustment", "Absent amount", "OT hours", "OT rate", "OT amount", "Hazira bonus", "Advance balance", "Advance deduction", "Outstanding loan", "Loan deduction", "Additional deduction", "Total salary", "Actions"].map((heading) => <th key={heading} className="px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">
        {entries.map((entry) => {
          const editing = editingEntryId === entry.id;
          const controls = [
            ["absent_days", "Absent days", "1"], ["leave_days", "Leave days", "1"],
            ["leave_amount", "Leave adjustment", "0.01"], ["absence_amount", "Absent amount", "0.01"],
            ["overtime_hours", "OT hours", "0.01"], ["overtime_rate", "OT rate", "0.01"],
            ["attendance_bonus", "Hazira bonus", "0.01"], ["advance_balance", "Advance balance", "0.01"],
            ["advance_deduction", "Advance deduction", "0.01"], ["outstanding_loan", "Outstanding loan", "0.01"],
            ["loan", "Loan deduction", "0.01"], ["other_deduction", "Additional deduction", "0.01"],
          ];
          const showValue = (key, value, label, step, allowNegative = false) => editing
            ? <input aria-label={`${entry.employee_name} ${label}`} type="number" min={allowNegative ? undefined : "0"} max={["absent_days", "leave_days"].includes(key) ? entry.total_days : undefined} step={step} value={value ?? 0} onChange={(event) => editEntry(entry.id, key, event.target.value)} className="w-28 rounded-lg border border-gray-200 px-2 py-1.5" />
            : <span>{["absent_days", "leave_days", "overtime_hours"].includes(key) ? value : money(value)}</span>;
          return <tr key={entry.id}>
            <td className="px-3 py-3"><div className="font-medium">{entry.employee_name}</div><div className="text-xs text-gray-500">{entry.employee_id} · {entry.designation} · {entry.total_days} days</div></td>
            <td className="px-3 py-3">{money(entry.base_salary)}</td><td className="px-3 py-3">{money(entry.per_day_rate)}</td>
            {controls.slice(0, 2).map(([key, label, step]) => <td key={key} className="px-3 py-3">{showValue(key, entry[key], label, step)}</td>)}
            {controls.slice(2, 4).map(([key, label, step]) => <td key={key} className="px-3 py-3">{showValue(key, entry[key], label, step, key === "leave_amount")}</td>)}
            {controls.slice(4, 6).map(([key, label, step]) => <td key={key} className="px-3 py-3">{showValue(key, entry[key], label, step)}</td>)}
            <td className="px-3 py-3">{money(Number(entry.overtime_hours || 0) * Number(entry.overtime_rate || 0))}</td>
            {controls.slice(6).map(([key, label, step]) => <td key={key} className="px-3 py-3">{showValue(key, entry[key], label, step)}</td>)}
            <td className="px-3 py-3 font-semibold text-emerald-800">{money(payrollPreview(entry))}</td>
            <td className="px-3 py-3"><div className="flex gap-2">{editing ? <><button type="button" disabled={busy} onClick={() => saveEntry(entry)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Save</button><button type="button" onClick={() => { setEditingEntryId(null); loadSheet().catch((err) => setSheetLoadError(apiErrorMessage(err, "Could not reload the salary sheet."))); }} className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs">Cancel</button></> : <button type="button" disabled={busy} onClick={() => setEditingEntryId(entry.id)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800 disabled:opacity-50">Update</button>}<button type="button" disabled={busy} onClick={() => deleteEntry(entry)} className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Delete</button></div></td>
          </tr>;
        })}
        {sheetLoading && <tr><td className="px-3 py-8 text-center text-gray-500" colSpan="18">Loading salary sheet…</td></tr>}
        {!sheetLoading && !sheetLoadError && !entries.length && <tr><td className="px-3 py-8 text-center text-gray-500" colSpan="18">No rows for {month}. Create or open a salary sheet to begin.</td></tr>}
      </tbody></table></div>
    </section>
  </div>;
}
