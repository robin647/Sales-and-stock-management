import { useEffect, useState } from "react";

export default function EmailVerificationForm({ email, expiresAt, busy, onSubmit, onResend, onBack, submitLabel = "Verify email" }) {
  const [otp, setOtp] = useState("");
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 500); return () => clearInterval(timer); }, []);
  useEffect(() => { setOtp(""); setNow(Date.now()); }, [expiresAt]);
  const seconds = Math.max(0, Math.ceil((new Date(expiresAt).getTime() - now) / 1000));
  return <form onSubmit={event => { event.preventDefault(); onSubmit(otp); }} className="space-y-4">
    <p className="login-form-subtitle text-sm">Enter the 6-digit code sent to <strong>{email}</strong>. Check Spam if it is missing.</p>
    <label className="login-label block text-sm" htmlFor="email-otp">Verification code</label>
    <input id="email-otp" autoFocus required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={otp} onChange={event => setOtp(event.target.value.replace(/[^0-9]/g, "").slice(0, 6))} className="login-input w-full rounded-xl border px-4 py-3 text-center text-2xl tracking-[0.5em]" aria-describedby="otp-time-left" />
    <p id="otp-time-left" role="status" className="text-sm text-gray-500">{seconds > 0 ? `Code expires in ${seconds}s` : "This code has expired. Request a new code."}</p>
    <button className="login-submit w-full rounded-xl py-3 text-sm font-semibold" disabled={busy || seconds === 0 || otp.length !== 6}>{busy ? "Please wait…" : submitLabel}</button>
    <div className="flex items-center justify-between gap-3 text-sm"><button type="button" disabled={busy || seconds > 0} onClick={onResend} className="text-brand-700 disabled:opacity-40">Resend code</button><button type="button" disabled={busy} onClick={onBack} className="text-gray-500">Change email / go back</button></div>
  </form>;
}
