import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { authApi } from "../api/endpoints";
import { SiteFooter } from "../components/SiteFooter";
import EmailVerificationForm from "../components/EmailVerificationForm";
import { errorMessage } from "../utils/apiError";

export default function CustomerSignup() {
  const navigate = useNavigate(), location = useLocation();
  const [form, setForm] = useState({ name: "", email: "", phone_number: "", password: "" });
  const [error, setError] = useState(""), [busy, setBusy] = useState(false), [expiresAt, setExpiresAt] = useState("");
  async function requestCode(event) {
    event?.preventDefault(); setBusy(true); setError("");
    try { const response = await authApi.requestEmailOtp(form.email.trim(), "signup"); setExpiresAt(response.data.expires_at); }
    catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  async function createAccount(otp) {
    setBusy(true); setError("");
    try { await authApi.signup({ ...form, email: form.email.trim(), otp }); navigate("/login", { replace: true, state: { customerCreated: true, email: form.email, returnTo: location.state?.returnTo } }); }
    catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  return <div className="login-page flex min-h-screen flex-col items-center justify-center px-4 py-10"><div className="w-full max-w-md"><Link to="/" className="login-brand mb-7 block text-center"><span className="login-title block text-2xl font-bold">MAHIR SHERWANI</span><span className="login-subtitle mt-2 block text-sm">Your next occasion starts here.</span></Link><section className="login-card rounded-2xl border p-6 sm:p-8"><h1 className="login-form-title mb-2 text-xl font-semibold">{expiresAt ? "Verify your email" : "Create your customer account"}</h1><p className="login-form-subtitle mb-6 text-sm">{expiresAt ? "One quick step to secure your account." : "Sign up with email, verify it, then sign in with your own password."}</p>{error && <p role="alert" className="login-error mb-4 rounded-lg border px-3 py-2.5 text-sm">{error}</p>}{expiresAt ? <EmailVerificationForm email={form.email} expiresAt={expiresAt} busy={busy} onSubmit={createAccount} onResend={requestCode} onBack={() => { setExpiresAt(""); setError(""); }} submitLabel="Verify & create account" /> : <form onSubmit={requestCode} className="space-y-4">{[["name", "Full name", "text", "name"], ["email", "Email address", "email", "email"], ["phone_number", "Mobile number · optional", "tel", "tel"], ["password", "Create a password", "password", "new-password"]].map(([key, label, type, autoComplete]) => <label key={key} className="login-label block text-sm font-semibold">{label}<input required={key !== "phone_number"} type={type} autoComplete={autoComplete} minLength={key === "password" ? 8 : undefined} maxLength={key === "name" ? 150 : key === "phone_number" ? 20 : key === "email" ? 254 : undefined} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} className="login-input mt-1 w-full rounded-xl border px-3.5 py-3 text-sm" /></label>)}<p className="text-xs text-gray-500">We will email a six-digit code, valid for one minute. Your account is created only after verification.</p><button disabled={busy} className="login-submit w-full rounded-xl py-3 text-sm font-semibold">{busy ? "Sending code…" : "Send verification code"}</button></form>}</section><p className="login-help mt-6 text-center text-sm">Already have an account? <Link className="font-semibold text-brand-600" to="/login">Sign in</Link></p></div><div className="mt-8 w-full"><SiteFooter className="login-footer" /></div></div>;
}
