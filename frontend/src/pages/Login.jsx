import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { messageOf } from "../services/api";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const user = await login(f.email, f.password);
      nav(user.role === "worker" ? "/worker/dashboard" : user.role === "employer" ? "/employer/dashboard" : "/admin/dashboard");
    } catch (error) {
      setErr(messageOf(error, "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <p className="eyebrow">WELCOME BACK</p>
        <h1>Sign in to LabourLink</h1>
        {err && <div className="error" data-testid="login-error">{err}</div>}
        <label className="field">
          <span>Email or mobile number</span>
          <input data-testid="login-identifier-input" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />
        </label>
        <label className="field">
          <span>Password</span>
          <div className="pw-wrap">
            <input
              data-testid="login-password-input"
              type={showPw ? "text" : "password"}
              value={f.password}
              onChange={(e) => setF({ ...f, password: e.target.value })}
              required
            />
            <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} aria-label={showPw ? "Hide password" : "Show password"}>
              {showPw ? "🙈" : "👁️"}
            </button>
          </div>
        </label>
        <div style={{ textAlign: "right", marginTop: -6 }}>
          <Link to="/forgot-password" style={{ fontSize: 13, color: "var(--teal)" }}>Forgot password?</Link>
        </div>
        <button data-testid="login-submit-button" className="btn primary" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
        <p>New here? <Link to="/register">Create an account</Link></p>
      </form>
    </div>
  );
}
