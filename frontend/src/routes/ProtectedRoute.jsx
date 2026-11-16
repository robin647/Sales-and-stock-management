import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function ProtectedRoute({ children, requireAdmin = false, requireShowroom = false, requireCommerce = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null;
  if (!user) return <Navigate to={requireShowroom ? "/showroom/login" : "/admin/login"} state={{ returnTo: location.pathname + location.search }} replace />;
  if (user.role === "customer") return <Navigate to="/" replace />;
  if (requireCommerce && !["admin", "ecommerce_staff"].includes(user.role)) return <Navigate to="/" replace />;
  if (requireAdmin && user.role !== "admin") return <Navigate to="/" replace />;
  if (requireShowroom && user.role !== "showroom_user") return <Navigate to="/" replace />;

  return children;
}
