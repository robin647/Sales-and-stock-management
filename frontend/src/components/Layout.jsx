import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const linkClass = ({ isActive }) =>
  `block px-4 py-2 rounded-lg text-sm font-medium ${
    isActive ? "bg-brand-500 text-white" : "text-gray-600 hover:bg-gray-100"
  }`;

export default function Layout({ children }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="font-semibold text-brand-700">Mahir Sherwani</div>
          <div className="text-xs text-gray-500 mt-1">
            {isAdmin ? "Admin Panel" : user?.showroomName}
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {isAdmin ? (
            <>
              <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
              <NavLink to="/showrooms" className={linkClass}>Showrooms</NavLink>
              <NavLink to="/products" className={linkClass}>Products</NavLink>
              <NavLink to="/reports" className={linkClass}>Reports</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
              <NavLink to="/stock" className={linkClass}>Stock Entry</NavLink>
              <NavLink to="/balance" className={linkClass}>Balance Entry</NavLink>
              <NavLink to="/reports" className={linkClass}>Reports</NavLink>
            </>
          )}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <div className="text-sm text-gray-700 mb-2">{user?.fullName}</div>
          <button
            onClick={handleLogout}
            className="w-full text-sm text-left px-4 py-2 rounded-lg text-red-600 hover:bg-red-50"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-y-auto">{children}</main>
    </div>
  );
}
