import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { Empty, ErrorBox, Loading, Badge, CardSkeleton } from "../components/States";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function WorkerDashboard() {
  const [jobs, setJobs] = useState([]);
  const [assigned, setAssigned] = useState([]);
  const [earn, setEarn] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/workers/jobs"), api.get("/workers/earnings"), api.get("/workers/assigned")])
      .then(([a, b, c]) => {
        setJobs(a.data.data || []);
        setEarn(b.data.data);
        setAssigned(c.data.data || []);
      })
      .catch((e) => setErr(messageOf(e, "Dashboard error")))
      .finally(() => setLoading(false));
  }, []);

  // Build last-6-months earnings chart data from transactions
  const chartData = React.useMemo(() => {
    const txns = earn?.transactions || [];
    const months = {};
    txns.forEach((t) => {
      if (t.kind !== "credit" || !t.date) return;
      const d = new Date(t.date);
      const key = d.toLocaleString("default", { month: "short", year: "2-digit" });
      months[key] = (months[key] || 0) + (t.amount || 0);
    });
    const entries = Object.entries(months).slice(-6);
    return entries.length > 0
      ? entries.map(([month, amount]) => ({ month, amount }))
      : [{ month: "No data", amount: 0 }];
  }, [earn]);

  if (loading) return (
    <div className="page">
      <h1>Worker dashboard</h1>
      <div className="stats">{[1,2,3,4].map((n) => <CardSkeleton key={n} />)}</div>
    </div>
  );

  return (
    <div className="page">
      <h1>Worker dashboard</h1>
      <ErrorBox text={err} />

      {/* Stats */}
      <div className="stats">
        <div className="card stat"><b>Wallet</b><strong>₹{earn?.wallet?.balance || 0}</strong></div>
        <div className="card stat"><b>Total earned</b><strong>₹{earn?.wallet?.total_earnings || 0}</strong></div>
        <div className="card stat"><b>Matched jobs</b><strong>{jobs.length}</strong></div>
        <div className="card stat"><b>Active jobs</b><strong>{assigned.filter((x) => x.status !== "Completed").length}</strong></div>
      </div>

      {/* Earnings chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ marginTop: 0 }}>Earnings history</h2>
        {(earn?.transactions || []).filter((t) => t.kind === "credit").length === 0 ? (
          <Empty icon="💰" title="No earnings yet." text="Complete jobs to see your earnings here." />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `₹${v}`} />
              <Tooltip formatter={(v) => [`₹${v}`, "Earned"]} />
              <Bar dataKey="amount" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={i === chartData.length - 1 ? "#0b4f52" : "#0e6a6e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Recent transactions */}
      {(earn?.transactions || []).length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ marginTop: 0 }}>Recent transactions</h2>
          <div style={{ display: "grid", gap: 8 }}>
            {earn.transactions.slice(0, 5).map((t, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{t.description || "Transaction"}</div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>{t.date ? new Date(t.date).toLocaleDateString() : ""}</div>
                </div>
                <span style={{ fontWeight: 700, color: t.kind === "credit" ? "var(--ok)" : "var(--danger)" }}>
                  {t.kind === "credit" ? "+" : "-"}₹{t.amount}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assigned jobs */}
      <h2>Your jobs</h2>
      {assigned.length === 0 ? (
        <Empty icon="💼" title="No assigned jobs yet." text="Apply to an open job to get started." />
      ) : (
        <div className="grid cols-2">{assigned.map((a) => (
          <div className="card" key={a.id}>
            <Badge>{a.status}</Badge>
            <h3>{a.job?.title}</h3>
            <p>₹{a.agreed_wage || a.job?.wage}</p>
            <div className="actions">
              <Link className="btn ghost" to={"/jobs/" + a.job.id}>Open</Link>
              {["Accepted", "Assigned", "Ongoing"].includes(a.status) && (
                <Link className="btn secondary" to={`/jobs/${a.job.id}/track`}>Share location</Link>
              )}
            </div>
          </div>
        ))}</div>
      )}

      {/* Recommended jobs */}
      <h2>Recommended near you</h2>
      {jobs.length === 0 ? (
        <Empty icon="🗺️" title="No jobs available in your area." text="Update your skills and location in Profile." />
      ) : (
        <div className="grid cols-3">{jobs.slice(0, 9).map((j) => (
          <div className="card" key={j.id}>
            <h3>{j.title}</h3>
            <p style={{ color: "var(--muted)", fontSize: 13 }}>{j.location}</p>
            <p style={{ fontSize: 13 }}>Match {j.match_score} · ₹{j.wage}</p>
            <Link className="btn ghost" to={"/jobs/" + j.id}>View</Link>
          </div>
        ))}</div>
      )}
    </div>
  );
}
