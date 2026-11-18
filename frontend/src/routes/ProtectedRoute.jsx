import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function ProtectedRoute({ children, requireAdmin = false, requireShowroom = false, requireCommerce = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return null;
  const allowed = user && (
    requireShowroom ? user.role === "showroom_user" :
    requireCommerce ? ["admin", "ecommerce_staff"].includes(user.role) :
    requireAdmin ? user.role === "admin" : user.role !== "customer"
  );
  if (!allowed) {
    return <Navigate to={requireShowroom ? "/showroom/login" : "/admin/login"} state={{ returnTo: location.pathname + location.search }} replace />;
  }

  return children;
}
