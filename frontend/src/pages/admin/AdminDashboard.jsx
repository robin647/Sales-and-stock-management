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
  const business = data.all_time_summary || {};
  const costs = business.costs || {};
  const sales = business.sales || {};
  const productsSold = business.products_sold || {};
  const dues = business.dues || {};
  const selectedMonth = formatMonth(data.period || month);

  return (
    <div className="space-y-8">
      <header className="dashboard-heading">
        <div>
          <p className="dashboard-eyebrow">Business overview</p>
          <h1>Admin Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">All-time business totals, with a monthly showroom view for {selectedMonth}.</p>
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

      <section aria-labelledby="business-overview-title" className="space-y-4">
        <div className="dashboard-section-heading">
          <div><h2 id="business-overview-title">Business overview · all time</h2><p>Combined operating costs, sales, production, and outstanding balances</p></div>
          <span className="dashboard-section-tag">All business units</span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Operating Cost" value={business.total_cost} description="Payroll, showroom salary, swing, producer & operating costs" accent="rose" />
          <StatCard label="Total Sales" value={business.total_sales} description="Showroom + wholesale, after wholesale returns" accent="green" />
          <StatCard label="Products Produced" value={business.total_products_produced} currency={false} description="Active swing lots" accent="gold" />
          <StatCard label="Products Sold" value={productsSold.total} currency={false} description="Showroom + wholesale quantities" accent="blue" />
        </div>
      </section>

      <section aria-labelledby="business-costs-title" className="space-y-4">
        <div className="dashboard-section-heading">
          <div><h2 id="business-costs-title">Cost breakdown</h2><p>All-time cost by business area</p></div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard label="Employee Salaries" value={costs.employee_salary} description="Total calculated salary from saved salary sheets" accent="blue" />
          <StatCard label="Showroom Salary" value={costs.showroom_salary} description="Salary recorded in showroom daily balances" accent="blue" />
          <StatCard label="Swing Operator Cost" value={costs.swing_operator_cost} description="Active lot quantity × rate" accent="gold" />
          <StatCard label="Producer Cost" value={costs.producer_cost} description="Active producer cost records" accent="green" />
          <StatCard label="Other Costs" value={costs.other_cost} description="Active other-cost records" accent="gold" />
          <StatCard label="Showroom Expenses" value={costs.showroom_expenses} description="Recorded in showroom daily balances" accent="rose" />
        </div>
      </section>

      <section aria-labelledby="business-cashflow-title" className="space-y-4">
        <div className="dashboard-section-heading">
          <div><h2 id="business-cashflow-title">Sales, cash & balances</h2><p>All-time sales and cash recorded across the business</p></div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Showroom Sales" value={sales.showroom} description="All recorded showroom sales" accent="green" />
          <StatCard label="Wholesale Sales" value={sales.wholesale} description="Net of recorded returns" accent="blue" />
          <StatCard label="Total Cash Received" value={sales.total_cash_received} description="Showroom cash + wholesale cash payments" accent="gold" />
          <StatCard label="Wholesale Due" value={dues.wholesale_receivable} description="Customer receivable balance" accent="rose" />
          <StatCard label="Showroom Cash" value={sales.showroom_cash} description="Cash sales recorded by showrooms" accent="blue" />
          <StatCard label="Wholesale Cash" value={sales.wholesale_cash} description="Cash payments from wholesale accounts" accent="green" />
          <StatCard label="Swing Operator Due" value={dues.swing_operator_payable} description="Outstanding amount payable to operators" accent="rose" />
          <StatCard label="Producer Due" value={dues.producer_payable} description="Producer cost less recorded payments" accent="gold" />
        </div>
        <p className="text-xs text-gray-500">Showroom sales are recorded as cash/card sales; receivable due is tracked in wholesale accounts. Swing and producer balances are payables.</p>
      </section>

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
