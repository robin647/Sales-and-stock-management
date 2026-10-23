import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { reportApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

const money = (amount) => `\u09F3 ${Number(amount || 0).toLocaleString("en-BD", { maximumFractionDigits: 0 })}`;
const currentMonth = () => localDateString().slice(0, 7);

function formatMonth(value) {
  const [year, month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(new Date(year, month - 1));
}

function StatCard({ label, value, description, currency = true, accent = "green" }) {
  const accentStyles = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-800",
    gold: "border-amber-200 bg-amber-50 text-amber-800",
    blue: "border-sky-200 bg-sky-50 text-sky-800",
    rose: "border-rose-200 bg-rose-50 text-rose-800",
  };
  return (
    <article className="dashboard-stat-card">
      <div className="flex items-start justify-between gap-3">
        <p className="dashboard-stat-label">{label}</p>
        <span className={`dashboard-stat-mark ${accentStyles[accent]}`} aria-hidden="true" />
      </div>
      <p className="dashboard-stat-value">{currency ? money(value) : Number(value || 0).toLocaleString()}</p>
      {description && <p className="dashboard-stat-description">{description}</p>}
    </article>
  );
}

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [month, setMonth] = useState(currentMonth);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const [year, selectedMonth] = month.split("-").map(Number);
    setLoading(true);
    setError("");
    reportApi
      .dashboard({ year, month: selectedMonth })
      .then((res) => {
        if (active) setData(res.data);
      })
      .catch(() => {
        if (active) setError("Could not load dashboard data.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [month]);

  if (error) return <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-800">{error}</div>;
  if (loading || !data) return <div className="rounded-xl border border-gray-200 bg-white p-5 text-sm font-medium text-gray-600">Loading dashboard...</div>;

  const wholesale = data.wholesale_summary || {};
  const selectedMonth = formatMonth(data.period || month);

  return (
    <div className="space-y-8">
      <header className="dashboard-heading">
        <div>
          <p className="dashboard-eyebrow">Business overview</p>
          <h1>Admin Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">Showroom performance for {selectedMonth}, with wholesale account totals.</p>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-600">
          Month
          <input
            aria-label="Dashboard month"
            type="month"
            value={month}
            onChange={(event) => setMonth(event.target.value)}
            className="dashboard-date-chip border-0"
          />
        </label>
      </header>

      <section aria-labelledby="showroom-overview-title" className="space-y-4">
        <div className="dashboard-section-heading">
          <div><h2 id="showroom-overview-title">Showroom monthly overview</h2><p>Combined totals for {selectedMonth}</p></div>
          <span className="dashboard-section-tag">{Number(data.total_showrooms || 0)} showrooms</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          <StatCard label="Total Sales" value={data.total_sale} description="All showrooms this month" accent="green" />
          <StatCard label="Cash Sales" value={data.cash_sale} description="Cash received this month" accent="blue" />
          <StatCard label="Card Sales" value={data.card_sale} description="Card payments this month" accent="gold" />
          <StatCard label="Expenses" value={data.expense} description="Recorded this month" accent="rose" />
          <StatCard label="Deposits" value={data.deposit} description="Deposited this month" accent="blue" />
          <StatCard label="Closing Cash" value={data.closing_balance} description="Latest closing balance per showroom" accent="green" />
        </div>
      </section>

      <section aria-labelledby="wholesale-overview-title" className="space-y-4">
        <div className="dashboard-section-heading">
          <div><h2 id="wholesale-overview-title">Wholesale overview</h2><p>Combined invoice and Easy Wholesale accounts · all time</p></div>
          <span className="dashboard-section-tag dashboard-section-tag-gold">Wholesale</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
          <StatCard label="Total Parties" value={wholesale.total_parties} currency={false} description={`${Number(wholesale.active_parties || 0).toLocaleString()} active accounts`} accent="blue" />
          <StatCard label="Net Wholesale Sales" value={wholesale.total_sales} description="After recorded returns" accent="green" />
          <StatCard label="Outstanding Due" value={wholesale.total_due} description="Amount still receivable" accent="rose" />
          <StatCard label="Payments Received" value={wholesale.total_payments} description="Invoice + Easy payments" accent="blue" />
          <StatCard label="Party Credit" value={wholesale.total_credit} description="Customer credit balance" accent="gold" />
        </div>
      </section>

      <section className="dashboard-chart-panel">
        <div className="dashboard-section-heading mb-4">
          <div><h2>Showroom sales comparison</h2><p>Total sales for {selectedMonth}, by showroom</p></div>
        </div>
        {data.showroom_wise?.length ? (
          <div className="h-[300px] w-full sm:h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.showroom_wise} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e6e9e2" vertical={false} />
                <XAxis dataKey="showroom__name" tick={{ fontSize: 12, fill: "#59685e" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#59685e" }} axisLine={false} tickLine={false} width={72} tickFormatter={(value) => Number(value).toLocaleString()} />
                <Tooltip formatter={(value) => money(value)} cursor={{ fill: "#edf3ed" }} />
                <Bar dataKey="total_sale" fill="#176b52" radius={[7, 7, 0, 0]} maxBarSize={64} name="Showroom sales" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <p className="rounded-xl bg-gray-50 px-4 py-8 text-center text-sm text-gray-600">No showroom sales have been recorded for this month.</p>}
      </section>
    </div>
  );
}
