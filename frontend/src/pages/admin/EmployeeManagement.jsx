import { useEffect, useState } from "react";
import { employeeApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

const monthNow = () => localDateString().slice(0, 7);
const money = (value) => `৳ ${Number(value || 0).toLocaleString("en-BD", { maximumFractionDigits: 2 })}`;
const fieldClass = "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-emerald-500";

export default function EmployeeManagement() {
  const [employees, setEmployees] = useState([]);
  const [entries, setEntries] = useState([]);
  const [month, setMonth] = useState(monthNow);
  const [form, setForm] = useState({ name: "", employee_id: "", designation: "", salary: "" });
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [employeeEdit, setEmployeeEdit] = useState({ name: "", employee_id: "", designation: "", salary: "" });
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadEmployees() {
    const response = await employeeApi.list();
    setEmployees(response.data.results || response.data);
  }

  async function loadSheet(selectedMonth = month) {
    const response = await employeeApi.salaryEntries(selectedMonth);
    setEntries(response.data.results || response.data);
  }

  useEffect(() => { loadEmployees().catch(() => setError("Could not load employees.")); }, []);
  useEffect(() => { loadSheet(month).catch(() => setEntries([])); }, [month]);

  async function addEmployee(event) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      await employeeApi.create({ ...form, salary: Number(form.salary) });
      setForm({ name: "", employee_id: "", designation: "", salary: "" });
      await loadEmployees(); setMessage("Employee added successfully.");
    } catch (err) { setError(err.response?.data?.employee_id?.[0] || err.response?.data?.detail || "Could not add employee. Check the fields and employee ID."); }
    finally { setBusy(false); }
  }

  async function createSheet() {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await employeeApi.createSalarySheet(month);
      setEntries(response.data); setMessage(`Salary sheet ready for ${month}.`);
    } catch (err) { setError(err.response?.data?.detail || "Could not create salary sheet."); }
    finally { setBusy(false); }
  }

  function editEntry(id, key, value) {
    setEntries((current) => current.map((entry) => entry.id === id ? { ...entry, [key]: value } : entry));
  }

  async function saveEntry(entry) {
    setBusy(true); setError("");
    try {
      await employeeApi.updateSalaryEntry(entry.id, {
        absent_days: Number(entry.absent_days), leave_days: Number(entry.leave_days),
        overtime_hours: Number(entry.overtime_hours), overtime_rate: Number(entry.overtime_rate),
        attendance_bonus: Number(entry.attendance_bonus), loan: Number(entry.loan),
        other_deduction: Number(entry.other_deduction),
      });
      await loadSheet(); setEditingEntryId(null); setMessage(`${entry.employee_name}'s salary updated.`);
    } catch (err) { setError(err.response?.data?.absent_days?.[0] || "Could not update salary. Check the entered values."); }
    finally { setBusy(false); }
  }

  function beginEmployeeEdit(employee) {
    setEditingEmployee(employee.id);
    setEmployeeEdit({ name: employee.name, employee_id: employee.employee_id, designation: employee.designation, salary: employee.salary });
  }

  async function saveEmployeeEdit(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await employeeApi.update(editingEmployee, { ...employeeEdit, salary: Number(employeeEdit.salary) });
      setEditingEmployee(null); await loadEmployees(); setMessage("Employee details updated.");
    } catch (err) { setError(err.response?.data?.employee_id?.[0] || "Could not update employee details."); }
    finally { setBusy(false); }
  }

  async function deleteEmployee(employee) {
    if (!window.confirm(`Delete ${employee.name} (${employee.employee_id}) from active employee list?`)) return;
    setBusy(true); setError("");
    try {
      await employeeApi.delete(employee.id); await loadEmployees();
      await loadSheet(); setMessage(`${employee.name} removed from the active employee list.`);
    } catch { setError("Could not delete employee."); }
    finally { setBusy(false); }
  }

  return <div className="space-y-6">
    <header className="dashboard-heading"><div><p className="dashboard-eyebrow">Team and payroll</p><h1>Employee Management</h1><p className="mt-1 text-sm text-gray-600">Add employees and prepare monthly salary sheets.</p></div></header>
    {(error || message) && <div role={error ? "alert" : "status"} className={`rounded-xl border p-3 text-sm ${error ? "border-rose-200 bg-rose-50 text-rose-800" : "border-emerald-200 bg-emerald-50 text-emerald-800"}`}>{error || message}</div>}

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>Add employee</h2><p>Set the employee’s monthly salary and role.</p></div></div>
      <form onSubmit={addEmployee} className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <input className={fieldClass} placeholder="Employee name" aria-label="Employee name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className={fieldClass} placeholder="Employee ID" aria-label="Employee ID" required value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} />
        <input className={fieldClass} placeholder="Designation" aria-label="Designation" required value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
        <input className={fieldClass} type="number" min="0" step="0.01" placeholder="Monthly salary" aria-label="Monthly salary" required value={form.salary} onChange={(e) => setForm({ ...form, salary: e.target.value })} />
        <button disabled={busy} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">Add employee</button>
      </form>
      {editingEmployee && <form onSubmit={saveEmployeeEdit} className="mt-4 grid grid-cols-1 gap-3 rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 sm:grid-cols-2 xl:grid-cols-5"><input className={fieldClass} aria-label="Edit employee name" required value={employeeEdit.name} onChange={(e) => setEmployeeEdit({ ...employeeEdit, name: e.target.value })} /><input className={fieldClass} aria-label="Edit employee ID" required value={employeeEdit.employee_id} onChange={(e) => setEmployeeEdit({ ...employeeEdit, employee_id: e.target.value })} /><input className={fieldClass} aria-label="Edit designation" required value={employeeEdit.designation} onChange={(e) => setEmployeeEdit({ ...employeeEdit, designation: e.target.value })} /><input className={fieldClass} aria-label="Edit monthly salary" type="number" min="0" step="0.01" required value={employeeEdit.salary} onChange={(e) => setEmployeeEdit({ ...employeeEdit, salary: e.target.value })} /><div className="flex gap-2"><button disabled={busy} className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white">Save</button><button type="button" onClick={() => setEditingEmployee(null)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">Cancel</button></div></form>}
      <div className="mt-5 overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="text-xs uppercase text-gray-500"><tr><th className="px-3 py-2">Employee</th><th className="px-3 py-2">ID</th><th className="px-3 py-2">Designation</th><th className="px-3 py-2">Monthly salary</th><th className="px-3 py-2">Action</th></tr></thead><tbody className="divide-y divide-gray-100">{employees.map((employee) => <tr key={employee.id}><td className="px-3 py-3 font-medium">{employee.name}</td><td className="px-3 py-3">{employee.employee_id}</td><td className="px-3 py-3">{employee.designation}</td><td className="px-3 py-3">{money(employee.salary)}</td><td className="px-3 py-3"><div className="flex gap-2"><button onClick={() => beginEmployeeEdit(employee)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800">Update</button><button disabled={busy} onClick={() => deleteEmployee(employee)} className="rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-700 disabled:opacity-50">Delete</button></div></td></tr>)}{!employees.length && <tr><td className="px-3 py-5 text-gray-500" colSpan="5">No employees added yet.</td></tr>}</tbody></table></div>
    </section>

    <section className="dashboard-chart-panel">
      <div className="dashboard-section-heading mb-4"><div><h2>Monthly salary sheet</h2><p>Perday rate = Net Salary ÷ month days. Leave amount = perday rate × leave days. Total = Net Salary − Absent Amount + Leave Amount + OT + Hazira Bownous − Loan − Deduct.</p></div></div>
      <div className="mb-4 flex flex-wrap items-end gap-3"><label className="text-sm font-medium text-gray-600">Salary month<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className={`${fieldClass} mt-1 block w-auto`} /></label><button disabled={busy || !employees.length} onClick={createSheet} className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">Create salary sheet</button><button disabled={busy || !entries.length} onClick={() => employeeApi.exportSalarySheet(month).catch(() => setError("Could not download salary sheet."))} className="rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50">Download monthly sheet</button></div>
      <div className="overflow-x-auto"><table className="min-w-[1550px] w-full text-left text-sm"><thead className="bg-gray-50 text-xs uppercase text-gray-500"><tr>{["Employee Name", "Net Salary", "Perday Rate", "Absent", "Leave / Chuti", "Leave Amount", "Absent Amount", "OT Hours", "OT Rete", "Hazira Bownous", "Loan", "Deduct", "Total Salary", "Action"].map((heading) => <th key={heading} className="px-3 py-3">{heading}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">{entries.map((entry) => { const editing = editingEntryId === entry.id; return <tr key={entry.id}><td className="px-3 py-3"><div className="font-medium">{entry.employee_name}</div><div className="text-xs text-gray-500">{entry.employee_id} · {entry.designation} · {entry.total_days} days</div></td>{[["base_salary", entry.base_salary, null], ["per_day_rate", entry.per_day_rate, null], ["absent_days", entry.absent_days, "1"], ["leave_days", entry.leave_days, "1"], ["leave_amount", entry.leave_amount, null], ["absence_deduction", entry.absence_deduction, null], ["overtime_hours", entry.overtime_hours, "0.01"], ["overtime_rate", entry.overtime_rate, "0.01"], ["attendance_bonus", entry.attendance_bonus, "0.01"], ["loan", entry.loan, "0.01"], ["other_deduction", entry.other_deduction, "0.01"], ["net_salary", entry.net_salary, null]].map(([key, value, step]) => <td key={key} className="px-3 py-3">{editing && step ? <input aria-label={`${entry.employee_name} ${key}`} type="number" min="0" max={["absent_days", "leave_days"].includes(key) ? entry.total_days : undefined} step={step} value={value} onChange={(e) => editEntry(entry.id, key, e.target.value)} className="w-24 rounded-lg border border-gray-200 px-2 py-1.5" /> : <span className={key === "net_salary" ? "font-semibold text-emerald-800" : ""}>{money(value)}</span>}</td>)}<td className="px-3 py-3">{editing ? <button disabled={busy} onClick={() => saveEntry(entry)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50">Save</button> : <button disabled={busy} onClick={() => setEditingEntryId(entry.id)} className="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50">Update</button>}</td></tr>; })}{!entries.length && <tr><td className="px-3 py-8 text-center text-gray-500" colSpan="14">Choose a month and create its salary sheet to begin.</td></tr>}</tbody></table></div>
    </section>
  </div>;
}
