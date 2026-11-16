import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { authApi } from "../api/endpoints";
import EmailVerificationForm from "../components/EmailVerificationForm";
import { errorMessage } from "../utils/apiError";

export default function VerifyEmail() {
  const location = useLocation(), navigate = useNavigate();
  const [email, setEmail] = useState(location.state?.email || ""), [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  async function request(event) { event?.preventDefault(); setBusy(true); setError(""); try { const res = await authApi.requestEmailOtp(email, "verify"); setExpiresAt(res.data.expires_at); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); } }
  async function verify(otp) { setBusy(true); setError(""); try { await authApi.verifyEmail(email, otp); navigate("/login", { replace: true, state: { email, emailVerified: true } }); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); } }
  return <main className="login-page flex min-h-screen items-center justify-center px-4 py-10"><section className="login-card w-full max-w-md rounded-2xl border p-7"><Link to="/">← MAHIR SHERWANI</Link><h1 className="login-form-title mb-3 mt-6 text-xl">Verify your existing customer account</h1><p className="login-form-subtitle mb-6 text-sm">Use the email saved on your account. Your orders and existing password stay with that account.</p>{error && <p className="login-error mb-4 rounded-lg border p-3 text-sm" role="alert">{error}</p>}{expiresAt ? <EmailVerificationForm email={email} expiresAt={expiresAt} busy={busy} onSubmit={verify} onResend={request} onBack={() => setExpiresAt("")} /> : <form onSubmit={request} className="space-y-4"><label className="login-label block text-sm">Saved email address<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} className="login-input mt-2 w-full rounded-xl border px-3 py-3" /></label><button className="login-submit w-full rounded-xl py-3" disabled={busy}>{busy ? "Sending…" : "Send verification code"}</button></form>}<Link className="mt-6 block text-sm text-brand-700" to="/login">Back to customer login</Link></section></main>;
}
