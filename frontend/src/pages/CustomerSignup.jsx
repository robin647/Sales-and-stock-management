import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api/endpoints";
import { SiteFooter } from "../components/SiteFooter.jsx";

function errorText(error) {
  const data = error.response?.data;
  if (!data) return "We could not create your account. Please try again.";
  return Object.values(data).flat().join(" ");
}

export default function CustomerSignup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone_number: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await authApi.signup(form);
      navigate("/login", { state: { customerCreated: true } });
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 py-10">
      <div className="relative w-full max-w-md">
        <Link to="/" className="login-brand mb-7 block text-center">
          <span className="login-brandmark mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white shadow-lg">MS</span>
          <span className="login-title block text-2xl font-bold">Mahir Sherwani</span>
          <span className="login-subtitle mt-1 block text-sm">A little more occasion, every day.</span>
        </Link>
        <div className="login-card rounded-2xl border p-6 sm:p-8">
          <div className="mb-5"><h1 className="login-form-title text-xl font-semibold">Create your account</h1><p className="login-form-subtitle mt-1 text-sm">Join us for new collections and special offers.</p></div>
          {error && <div role="alert" className="login-error mb-4 rounded-lg border px-3 py-2.5 text-sm font-medium">{error}</div>}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div><label className="login-label mb-1 block text-sm font-semibold" htmlFor="signup-name">Full name</label><input id="signup-name" className="login-input w-full rounded-xl border px-3.5 py-3 text-sm" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} autoComplete="name" required /></div>
            <div><label className="login-label mb-1 block text-sm font-semibold" htmlFor="signup-email">Email address</label><input id="signup-email" type="email" className="login-input w-full rounded-xl border px-3.5 py-3 text-sm" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" required /></div>
            <div><label className="login-label mb-1 block text-sm font-semibold" htmlFor="signup-mobile">Mobile number</label><input id="signup-mobile" type="tel" className="login-input w-full rounded-xl border px-3.5 py-3 text-sm" value={form.phone_number} onChange={(event) => setForm({ ...form, phone_number: event.target.value })} autoComplete="tel" placeholder="01XXXXXXXXX" required /></div>
            <div><label className="login-label mb-1 block text-sm font-semibold" htmlFor="signup-password">Password</label><input id="signup-password" type="password" className="login-input w-full rounded-xl border px-3.5 py-3 text-sm" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} autoComplete="new-password" minLength="8" required /></div>
            <button type="submit" disabled={loading} className="login-submit w-full rounded-xl bg-brand-500 py-3 text-sm font-semibold text-white">{loading ? "Creating account…" : "Create account"}</button>
          </form>
          <p className="login-help mt-5 text-center text-sm">Already have an account? <Link to="/login" className="font-semibold text-brand-600">Sign in</Link></p>
        </div>
      </div>
      <div className="relative mt-8 w-full"><SiteFooter className="login-footer" /></div>
    </div>
  );
}