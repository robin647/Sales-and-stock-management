import { useEffect, useState } from "react";
import { showroomApi, showroomUserApi } from "../../api/endpoints";

export default function Showrooms() {
  const [showrooms, setShowrooms] = useState([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [userForm, setUserForm] = useState({ username: "", password: "", showroom: "" });
  const [userError, setUserError] = useState("");
  const [userSuccess, setUserSuccess] = useState("");
  const [showUserForm, setShowUserForm] = useState(false);

  function loadShowrooms() {
    showroomApi.list().then((res) => setShowrooms(res.data.results || res.data));
  }

  useEffect(loadShowrooms, []);

  async function handleAddShowroom(e) {
    e.preventDefault();
    setError("");
    try {
      await showroomApi.create({ name, address, username, password });
      setName("");
      setAddress("");
      setUsername("");
      setPassword("");
      loadShowrooms();
    } catch (err) {
      setError(err.response?.data?.name?.[0] || err.response?.data?.detail || "Could not create showroom.");
    }
  }

  async function toggleActive(sr) {
    await showroomApi.update(sr.id, { is_active: !sr.is_active });
    loadShowrooms();
  }

  async function handleCreateUser(e) {
    e.preventDefault();
    setUserError("");
    setUserSuccess("");
    try {
      await showroomUserApi.create(userForm);
      setUserSuccess(`Showroom user "${userForm.username}" created successfully.`);
      setUserForm({ username: "", password: "", showroom: "" });
      setShowUserForm(false);
    } catch (err) {
      setUserError(
        JSON.stringify(err.response?.data?.errors || err.response?.data?.detail || "Failed to create user.")
      );
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-lg font-semibold">Showrooms</h1>

      <div className="bg-white rounded-2xl border border-gray-100 p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-2">Name</th>
              <th>Username</th>
              <th>Address</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {showrooms.map((sr) => (
              <tr key={sr.id} className="border-b border-gray-50">
                <td className="py-2 font-medium">{sr.name}</td>
                <td className="text-gray-600">{sr.username || "—"}</td>
                <td className="text-gray-500">{sr.address || "—"}</td>
                <td>
                  <span className={`text-xs px-2 py-1 rounded-full ${sr.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {sr.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button onClick={() => toggleActive(sr)} className="text-brand-600 text-xs hover:underline">
                    {sr.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleAddShowroom} className="bg-white rounded-2xl border border-gray-100 p-4 max-w-md">
        <div className="text-sm font-medium text-gray-700 mb-3">Add new showroom</div>
        {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
        <input
          placeholder="Showroom name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          placeholder="Username for login"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          type="password"
          placeholder="Password for login"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          placeholder="Address (optional)"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          className="w-full mb-3 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
        <button className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg">
          Add showroom
        </button>
      </form>

      {/* Create Showroom User Form (for admins to login) */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 max-w-md">
        <button
          onClick={() => setShowUserForm(!showUserForm)}
          className="text-sm font-medium text-gray-700 mb-3 hover:text-brand-600"
        >
          {showUserForm ? "Hide" : "Show"} - Create admin account for showroom
        </button>

        {showUserForm && (
          <form onSubmit={handleCreateUser} className="space-y-2">
            {userError && <div className="text-xs text-red-600 mb-2">{userError}</div>}
            {userSuccess && <div className="text-xs text-green-700 mb-2">{userSuccess}</div>}
            <select
              value={userForm.showroom}
              onChange={(e) => setUserForm({ ...userForm, showroom: e.target.value })}
              className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              required
            >
              <option value="">Select showroom</option>
              {showrooms.map((sr) => (
                <option key={sr.id} value={sr.id}>{sr.name}</option>
              ))}
            </select>
            <input
              placeholder="Admin username"
              value={userForm.username}
              onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
              className="w-full mb-2 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              required
            />
            <input
              type="password"
              placeholder="Admin password"
              value={userForm.password}
              onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
              className="w-full mb-3 border border-gray-300 rounded-lg px-3 py-2 text-sm"
              required
            />
            <button className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg">
              Create admin account
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
