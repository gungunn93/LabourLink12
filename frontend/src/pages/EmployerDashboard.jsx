import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { Badge, Empty, ErrorBox, Loading, CardSkeleton } from "../components/States";

export default function EmployerDashboard() {
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [extras, setExtras] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => Promise.all([
    api.get("/employers/jobs"),
    api.get("/applications"),
    api.get("/extra-requests"),
    api.get("/notifications"),
  ])
    .then(([a, b, c, d]) => {
      setJobs(a.data.data || []);
      setApps(b.data.data || []);
      setExtras(c.data.data || []);
      setNotifications((d.data.data || []).slice(0, 5));
    })
    .catch((e) => setErr(messageOf(e)))
    .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const extraStatus = async (id, status) => {
    try { await api.put(`/extra-requests/${id}/status`, { status }); load(); } catch (e) { setErr(messageOf(e)); }
  };

  if (loading) return (
    <div className="page">
      <h1>Employer dashboard</h1>
      <div className="stats">{[1,2,3,4].map((n) => <CardSkeleton key={n} />)}</div>
    </div>
  );

  return (
    <div className="page">
      <div className="job-head">
        <h1>Employer dashboard</h1>
        <Link className="btn primary" to="/employer/jobs/new">Post job</Link>
      </div>
      <ErrorBox text={err} />

      {/* Stats */}
      <div className="stats">
        <div className="card stat"><b>Jobs posted</b><strong>{jobs.length}</strong></div>
        <div className="card stat"><b>Applications</b><strong>{apps.length}</strong></div>
        <div className="card stat"><b>Open jobs</b><strong>{jobs.filter((j) => j.status === "Open").length}</strong></div>
        <div className="card stat"><b>Pending requests</b><strong>{extras.filter((x) => x.status === "Pending").length}</strong></div>
      </div>

      {/* Recent activity feed */}
      {notifications.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Recent activity</h2>
            <Link to="/notifications" style={{ fontSize: 13, color: "var(--teal)" }}>View all →</Link>
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {notifications.map((n) => (
              <div key={n.id} style={{
                display: "flex", gap: 12, alignItems: "flex-start",
                padding: "10px 0", borderBottom: "1px solid var(--line)",
                opacity: n.is_read ? 0.65 : 1,
              }}>
                <span style={{ fontSize: 20 }}>
                  {n.kind === "message" ? "💬" : n.kind === "payment" ? "💰" : n.kind === "job" ? "💼" : "🔔"}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{n.title}</div>
                  <div style={{ fontSize: 13, color: "var(--muted)" }}>{n.message}</div>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>{n.date ? new Date(n.date).toLocaleString() : ""}</div>
                </div>
                {!n.is_read && <span style={{ marginLeft: "auto", width: 8, height: 8, borderRadius: "50%", background: "var(--orange)", flexShrink: 0, marginTop: 6 }} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Job postings */}
      <h2>Your postings</h2>
      {jobs.length === 0 ? (
        <Empty icon="📋" title="No jobs posted yet." text="Publish a job to start receiving applications." />
      ) : (
        <div className="grid cols-3">{jobs.map((j) => (
          <div className="card" key={j.id}>
            <Badge>{j.status}</Badge>
            <h3>{j.title}</h3>
            <p style={{ color: "var(--muted)", fontSize: 13 }}>{j.location}</p>
            <p style={{ fontSize: 13 }}>₹{j.payable_amount || j.wage}</p>
            <div className="actions">
              <Link className="btn ghost" to={"/jobs/" + j.id}>View</Link>
              {["Assigned", "Ongoing"].includes(j.status) && (
                <Link className="btn secondary" to={`/jobs/${j.id}/track`}>Track worker</Link>
              )}
            </div>
          </div>
        ))}</div>
      )}

      {/* Extra payment requests */}
      <h2>Additional payment requests</h2>
      {extras.length === 0 ? (
        <Empty icon="📝" title="No extra-work requests." text="Assigned workers can request extra pay if the job grows." />
      ) : extras.map((x) => (
        <div className="card" key={x.id} style={{ marginBottom: 10 }}>
          <p>Job #{x.job_id} · ₹{x.amount} · <Badge>{x.status}</Badge></p>
          <p>{x.reason}</p>
          {x.status === "Pending" && (
            <div className="actions">
              <button className="btn primary" onClick={() => extraStatus(x.id, "Accepted")}>Approve</button>
              <button className="btn danger" onClick={() => extraStatus(x.id, "Rejected")}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
