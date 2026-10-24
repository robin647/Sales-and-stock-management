import { useEffect, useState } from "react";
import { reportApi } from "../../api/endpoints";
import { localDateString } from "../../utils/date";

function StatCard({ label, value, isCurrency = true }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 mt-1">
        {isCurrency ? `৳ ${Number(value).toLocaleString()}` : value}
      </div>
    </div>
  );
}

export default function ShowroomDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const today = localDateString();
    const [year, month] = today.split("-");
    reportApi
      .dashboard({ year, month })
      .then((res) => setData(res.data))
      .catch(() => setError("Could not load dashboard data."));
  }, []);

  if (error) return <div className="text-red-600 text-sm">{error}</div>;
  if (!data) return <div className="text-gray-500 text-sm">Loading dashboard...</div>;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-1">Monthly Overview</h1>
      <div className="mb-3 text-sm text-gray-500">Monthly statement for {data.period}</div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Total Sale" value={data.total_sale} />
        <StatCard label="Cash Sale" value={data.cash_sale} />
        <StatCard label="Card Sale" value={data.card_sale} />
        <StatCard label="Expense" value={data.expense} />
        <StatCard label="Salary" value={data.salary} />
        <StatCard label="Deposit" value={data.deposit} />
        <StatCard label="Closing Balance" value={data.closing_balance} />
        <StatCard label="Stock Received" value={data.stock_summary.received} isCurrency={false} />
        <StatCard label="Stock Sold" value={data.stock_summary.sold} isCurrency={false} />
        <StatCard label="Customer Returns" value={data.stock_summary.returned} isCurrency={false} />
        <StatCard label="Returned to Factory" value={data.stock_summary.returned_to_factory} isCurrency={false} />
      </div>
    </div>
  );
}
