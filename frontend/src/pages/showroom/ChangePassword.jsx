import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../../api/endpoints";
import { useAuth } from "../../context/AuthContext";

function getErrorMessage(error) {
  const response = error.response?.data;
  const fieldErrors = response?.errors || {};
  const messages = Object.entries(fieldErrors).flatMap(([field, values]) =>
    (Array.isArray(values) ? values : [values])
      .filter((value) => typeof value === "string")
      .map((value) => `${field.replaceAll("_", " ")}: ${value}`)
  );
  return messages.join(" ") || response?.detail || "Password could not be changed. Please check the fields.";
}

export default function ChangePassword() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [form, setForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (form.new_password !== form.confirm_password) {
      setError("New passwords do not match.");
      return;
    }

    setSaving(true);
    try {
      await authApi.changePassword(form);
      logout();
      navigate("/login", { replace: true, state: { passwordChanged: true } });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="max-w-xl space-y-5">
      <div>
        <h1 className="text-lg font-semibold">Change password</h1>
        <p className="mt-1 text-sm text-gray-500">Change the password for your showroom login. Your showroom name and username cannot be changed here.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-gray-100 bg-white p-5">
        {error && <div role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        {[
          ["current_password", "Current password", "current-password"],
          ["new_password", "New password", "new-password"],
          ["confirm_password", "Confirm new password", "new-password"],
        ].map(([key, label, autoComplete]) => (
          <label key={key} className="block text-sm text-gray-600">
            {label}
            <input
              type="password"
              autoComplete={autoComplete}
              required
              minLength={key === "current_password" ? undefined : 8}
              value={form[key]}
              onChange={(event) => setForm({ ...form, [key]: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900"
            />
          </label>
        ))}
        <p className="text-xs text-gray-500">Your new password must pass the same strength checks used when the account was created. You will need to sign in again after changing it.</p>
        <button type="submit" disabled={saving} className="w-full rounded-lg bg-brand-500 py-2.5 text-sm font-medium text-white disabled:opacity-60">
          {saving ? "Changing password…" : "Change password"}
        </button>
      </form>
    </section>
  );
}
