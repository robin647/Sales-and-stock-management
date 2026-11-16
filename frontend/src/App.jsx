import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";

import { legacyAdminPaths } from "./routes/paths";
const VerifyEmail = lazy(() => import("./pages/VerifyEmail.jsx"));
const Login = lazy(() => import("./pages/Login.jsx"));
const Storefront = lazy(() => import("./pages/Storefront.jsx"));
const CustomerSignup = lazy(() => import("./pages/CustomerSignup.jsx"));
const Reports = lazy(() => import("./pages/Reports.jsx"));
const AdminDashboard = lazy(() => import("./pages/admin/AdminDashboard.jsx"));
const CustomerSupport = lazy(() => import("./pages/CustomerSupport.jsx"));
const StorePage = lazy(() => import("./pages/StorePage.jsx"));
const EcommerceAdmin = lazy(() => import("./pages/admin/EcommerceAdmin.jsx"));
const Products = lazy(() => import("./pages/admin/Products.jsx"));
const CommerceManagement = lazy(() => import("./pages/admin/CommerceManagement.jsx"));
const Customers = lazy(() => import("./pages/admin/Customers.jsx"));
const ShopAccount = lazy(() => import("./pages/ShopAccount.jsx"));
const Showrooms = lazy(() => import("./pages/admin/Showrooms.jsx"));
const StockAdjustments = lazy(() => import("./pages/admin/StockAdjustments.jsx"));
const WholesaleParties = lazy(() => import("./pages/admin/WholesaleParties.jsx"));
const WholesaleSales = lazy(() => import("./pages/admin/WholesaleSales.jsx"));
const EasyWholesaleManagement = lazy(() => import("./pages/admin/EasyWholesaleManagement.jsx"));
const WholesaleReturns = lazy(() => import("./pages/admin/WholesaleReturns.jsx"));
const AllPartiesSummary = lazy(() => import("./pages/admin/AllPartiesSummary.jsx"));
const WholesaleReports = lazy(() => import("./pages/admin/WholesaleReports.jsx"));
const EmployeeManagement = lazy(() => import("./pages/admin/EmployeeManagement.jsx"));
const SwingManagement = lazy(() => import("./pages/admin/SwingManagement.jsx"));
const ProducerCostManagement = lazy(() => import("./pages/admin/ProducerCostManagement.jsx"));
const BalanceEntry = lazy(() => import("./pages/showroom/BalanceEntry.jsx"));
const ChangePassword = lazy(() => import("./pages/showroom/ChangePassword.jsx"));
const ShowroomDashboard = lazy(() => import("./pages/showroom/ShowroomDashboard.jsx"));
const StockEntry = lazy(() => import("./pages/showroom/StockEntry.jsx"));
import { WhatsAppButton } from "./components/SiteFooter.jsx";
import AIAssistantButton from "./components/AIAssistantButton.jsx";

function LegacyRoute() {
  const location = useLocation(), params = useParams();
  const { user, loading } = useAuth();
  if (loading) return null;
  let target = legacyAdminPaths[location.pathname];
  if (location.pathname.startsWith("/ecommerce")) target = `/admin/ecommerce/${params.module || "dashboard"}`;
  if (location.pathname === "/reports") target = user?.role === "showroom_user" ? "/showroom/reports" : "/admin/reports";
  if (location.pathname === "/stock") target = user?.role === "showroom_user" ? "/showroom/stock" : "/admin/stock-entry";
  if (location.pathname === "/balance") target = user?.role === "showroom_user" ? "/showroom/balance" : "/admin/balance-entry";
  if (location.pathname === "/change-password") target = "/showroom/change-password";
  return <Navigate to={(target || "/") + location.search + location.hash} state={location.state} replace />;
}

export default function App() {
  const { isAdmin } = useAuth();

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
      <Route path="/" element={<Storefront />} />
      <Route path="/shop" element={<Storefront />} />
      <Route path="/login" element={<Login portal="customer" />} />
      <Route path="/signup" element={<CustomerSignup />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/checkout" element={<ShopAccount />} />
      <Route path="/my-orders" element={<ShopAccount />} />
      <Route path="/support" element={<CustomerSupport />} />
      <Route path="/pages/:slug" element={<StorePage />} />
      <Route path="/admin/login" element={<Login portal="admin" />} />
      <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="/admin/ecommerce/:module?" element={<ProtectedRoute requireCommerce><EcommerceAdmin /></ProtectedRoute>} />
      {[
        ["dashboard", AdminDashboard], ["customers", Customers], ["showrooms", Showrooms],
        ["products", Products], ["stock-adjustments", StockAdjustments],
        ["wholesale/parties", WholesaleParties], ["wholesale/sales", WholesaleSales],
        ["wholesale/easy", EasyWholesaleManagement], ["wholesale/returns", WholesaleReturns],
        ["wholesale/summary", AllPartiesSummary], ["wholesale/reports", WholesaleReports],
        ["employees", EmployeeManagement], ["swing", SwingManagement],
        ["producer-cost-management", ProducerCostManagement], ["reports", Reports],
        ["stock-entry", StockEntry], ["balance-entry", BalanceEntry],
      ].map(([path, Page]) => <Route key={path} path={`/admin/${path}`} element={<ProtectedRoute requireAdmin><Layout><Page /></Layout></ProtectedRoute>} />)}
      <Route path="/admin/online-products" element={<ProtectedRoute requireAdmin><Layout><Products online /></Layout></ProtectedRoute>} />
      <Route path="/admin/online-stock" element={<ProtectedRoute requireAdmin><Layout><StockAdjustments online /></Layout></ProtectedRoute>} />
      <Route path="/admin/online-orders" element={<ProtectedRoute requireAdmin><Layout><CommerceManagement /></Layout></ProtectedRoute>} />
      <Route path="/showroom/login" element={<Login portal="showroom" />} />
      <Route path="/showroom" element={<Navigate to="/showroom/dashboard" replace />} />
      {[["dashboard", ShowroomDashboard], ["stock", StockEntry], ["balance", BalanceEntry], ["reports", Reports], ["change-password", ChangePassword]].map(([path, Page]) => <Route key={path} path={`/showroom/${path}`} element={<ProtectedRoute requireShowroom><Layout><Page /></Layout></ProtectedRoute>} />)}
      {Object.keys(legacyAdminPaths).map(path => <Route key={path} path={path} element={<LegacyRoute />} />)}
      {["/reports", "/stock", "/balance", "/change-password", "/ecommerce/:module?"].map(path => <Route key={path} path={path} element={<LegacyRoute />} />)}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
    {isAdmin && <AIAssistantButton />}
    <WhatsAppButton />
    </>
  );
}
