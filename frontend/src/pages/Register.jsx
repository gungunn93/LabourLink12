import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { persist } = useAuth();
  const [f, setF] = useState({
    name: "", email: "", password: "", phone: "",
    role: params.get("role") === "employer" ? "employer" : "worker",
    skills: "", experience: 0, location: "",
  });
  const [err, setErr] = useState("");
  const [showPw, setShowPw] = useState(false);
  const up = (e) => setF({ ...f, [e.target.name]: e.target.value });

  const reg = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      const r = await api.post("/auth/register", f);
      const data = r.data.data;
      persist(data.user, data.token);
      nav(data.user.role === "worker" ? "/worker/dashboard" : "/employer/dashboard");
    } catch (error) {
      setErr(messageOf(error, "Registration failed"));
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={reg}>
        <p className="eyebrow">CREATE ACCOUNT</p>
        <h1>Join LabourLink</h1>
        {err && <div className="error" data-testid="register-error">{err}</div>}
        <input name="name" placeholder="Full name" onChange={up} required />
        <input name="email" type="email" placeholder="Email" onChange={up} required />
        <input name="phone" placeholder="Mobile number (optional)" onChange={up} />
        <div className="pw-wrap">
          <input
            name="password"
            type={showPw ? "text" : "password"}
            placeholder="Password (min 8 characters)"
            onChange={up}
            required
            minLength={8}
          />
          <button type="button" className="pw-toggle" onClick={() => setShowPw(!showPw)} aria-label={showPw ? "Hide password" : "Show password"}>
            {showPw ? "🙈" : "👁️"}
          </button>
        </div>
        <select name="role" value={f.role} onChange={up}>
          <option value="worker">Worker</option>
          <option value="employer">Employer</option>
        </select>
        {f.role === "worker" && (
          <>
            <input name="skills" placeholder="Skills (comma separated)" onChange={up} />
            <input name="experience" type="number" placeholder="Years of experience" onChange={up} />
          </>
        )}
        <input name="location" placeholder="City / area" onChange={up} />
        <button data-testid="register-submit-button" className="btn primary">Create account</button>
        <p>Already registered? <Link to="/login">Login</Link></p>
      </form>
    </div>
  );
}
