import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

const Login = lazy(() => import("./pages/Login.jsx"));
const Reports = lazy(() => import("./pages/Reports.jsx"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard.jsx"));
const Products = lazy(() => import("./pages/admin/Products.jsx"));
const Showrooms = lazy(() => import("./pages/admin/Showrooms.jsx"));
const StockAdjustments = lazy(() => import("./pages/admin/StockAdjustments.jsx"));
const WholesaleParties = lazy(() => import("./pages/admin/WholesaleParties.jsx"));
const WholesaleSales = lazy(() => import("./pages/admin/WholesaleSales.jsx"));
const EasyWholesaleManagement = lazy(() => import("./pages/admin/EasyWholesaleManagement.jsx"));
const WholesaleReturns = lazy(() => import("./pages/admin/WholesaleReturns.jsx"));
const AllPartiesSummary = lazy(() => import("./pages/admin/AllPartiesSummary.jsx"));
const WholesaleReports = lazy(() => import("./pages/admin/WholesaleReports.jsx"));
const BalanceEntry = lazy(() => import("./pages/showroom/BalanceEntry.jsx"));
const ChangePassword = lazy(() => import("./pages/showroom/ChangePassword.jsx"));
const ShowroomDashboard = lazy(() => import("./pages/showroom/ShowroomDashboard.jsx"));
const StockEntry = lazy(() => import("./pages/showroom/StockEntry.jsx"));
import { WhatsAppButton } from "./components/SiteFooter.jsx";

function Home() {
  const { isAdmin } = useAuth();
  return isAdmin ? <AdminDashboard /> : <ShowroomDashboard />;
}

export default function App() {
  useEffect(() => {
    const preventWheelChange = (event) => {
      if (event.target instanceof HTMLInputElement && event.target.type === "number" && event.target === document.activeElement) {
        event.preventDefault();
      }
    };
    document.addEventListener("wheel", preventWheelChange, { capture: true, passive: false });
    return () => document.removeEventListener("wheel", preventWheelChange, true);
  }, []);

  return (
    <>
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-slate-600">Loading workspace…</div>}>
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout><Home /></Layout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/showrooms"
        element={
          <ProtectedRoute requireAdmin>
            <Layout><Showrooms /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ProtectedRoute requireAdmin>
            <Layout><Products /></Layout>
          </ProtectedRoute>
        }
      />
      <Route path="/stock-adjustments" element={<ProtectedRoute requireAdmin><Layout><StockAdjustments /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/parties" element={<ProtectedRoute requireAdmin><Layout><WholesaleParties /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/sales" element={<ProtectedRoute requireAdmin><Layout><WholesaleSales /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/easy" element={<ProtectedRoute requireAdmin><Layout><EasyWholesaleManagement /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/returns" element={<ProtectedRoute requireAdmin><Layout><WholesaleReturns /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/summary" element={<ProtectedRoute requireAdmin><Layout><AllPartiesSummary /></Layout></ProtectedRoute>} />
      <Route path="/wholesale/reports" element={<ProtectedRoute requireAdmin><Layout><WholesaleReports /></Layout></ProtectedRoute>} />

      <Route
        path="/stock"
        element={
          <ProtectedRoute>
            <Layout><StockEntry /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/balance"
        element={
          <ProtectedRoute>
            <Layout><BalanceEntry /></Layout>
          </ProtectedRoute>
        }
      />
      <Route path="/change-password" element={<ProtectedRoute requireShowroom><Layout><ChangePassword /></Layout></ProtectedRoute>} />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <Layout><Reports /></Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
    <WhatsAppButton />
    </>
  );
}
