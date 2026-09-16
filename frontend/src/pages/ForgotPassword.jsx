import React, { useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";

export default function ForgotPassword() {
  const [step, setStep] = useState("email"); // email | token | done
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const sendReset = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    setLoading(true);
    try {
      const r = await api.post("/auth/forgot-password", { email });
      const data = r.data.data || {};
      if (data.reset_token) {
        // Dev mode — token returned directly
        setToken(data.reset_token);
        setMsg("Dev mode: token pre-filled. Enter your new password.");
      } else {
        setMsg("If that email is registered, a reset link has been sent. Check your inbox.");
      }
      setStep("token");
    } catch (e) {
      setErr(messageOf(e, "Something went wrong"));
    } finally {
      setLoading(false);
    }
  };

  const doReset = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    if (password !== confirmPw) { setErr("Passwords do not match"); return; }
    if (password.length < 8) { setErr("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      setStep("done");
    } catch (e) {
      setErr(messageOf(e, "Reset failed. The token may have expired."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <p className="eyebrow">ACCOUNT RECOVERY</p>
        <h1>Reset password</h1>

        {err && <div className="error">{err}</div>}
        {msg && <div className="success">{msg}</div>}

        {step === "email" && (
          <form onSubmit={sendReset} style={{ display: "grid", gap: 12 }}>
            <label className="field">
              <span>Your registered email address</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            <button className="btn primary" disabled={loading}>
              {loading ? "Sending…" : "Send reset link"}
            </button>
            <p style={{ textAlign: "center" }}>
              <Link to="/login">Back to login</Link>
            </p>
          </form>
        )}

        {step === "token" && (
          <form onSubmit={doReset} style={{ display: "grid", gap: 12 }}>
            <label className="field">
              <span>Reset token</span>
              <input
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste token from email"
                required
              />
            </label>
            <label className="field">
              <span>New password</span>
              <div className="pw-wrap">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  required
                  minLength={8}
                />
                <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)}>
                  {showPw ? "🙈" : "👁️"}
                </button>
              </div>
            </label>
            <label className="field">
              <span>Confirm new password</span>
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                placeholder="Repeat password"
                required
              />
            </label>
            <button className="btn primary" disabled={loading}>
              {loading ? "Resetting…" : "Set new password"}
            </button>
          </form>
        )}

        {step === "done" && (
          <div style={{ textAlign: "center", display: "grid", gap: 16 }}>
            <div style={{ fontSize: 48 }}>✅</div>
            <h3>Password reset successfully!</h3>
            <p style={{ color: "var(--muted)" }}>You can now log in with your new password.</p>
            <Link className="btn primary" to="/login">Go to login</Link>
          </div>
        )}
      </div>
    </div>
  );
}
