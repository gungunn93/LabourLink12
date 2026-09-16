import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";

export default function EmployerDashboard() {
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [extras, setExtras] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => Promise.all([api.get("/employers/jobs"), api.get("/applications"), api.get("/extra-requests")])
    .then(([a, b, c]) => { setJobs(a.data.data || []); setApps(b.data.data || []); setExtras(c.data.data || []); })
    .catch((e) => setErr(messageOf(e)))
    .finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const extraStatus = async (id, status) => {
    try { await api.put(`/extra-requests/${id}/status`, { status }); load(); } catch (e) { setErr(messageOf(e)); }
  };

  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <div className="job-head">
        <h1>Employer dashboard</h1>
        <Link className="btn primary" to="/employer/jobs/new">Post job</Link>
      </div>
      <ErrorBox text={err} />
      <div className="stats">
        <div className="card stat"><b>Jobs</b><strong>{jobs.length}</strong></div>
        <div className="card stat"><b>Applications</b><strong>{apps.length}</strong></div>
        <div className="card stat"><b>Open jobs</b><strong>{jobs.filter((j) => j.status === "Open").length}</strong></div>
        <div className="card stat"><b>Extra requests</b><strong>{extras.filter((x) => x.status === "Pending").length}</strong></div>
      </div>
      <h2>Your postings</h2>
      {jobs.length === 0 ? <Empty title="You have not posted any jobs yet." text="Publish a job to start receiving applications." /> : (
        <div className="grid cols-3">{jobs.map((j) => (
          <div className="card" key={j.id}>
            <Badge>{j.status}</Badge>
            <h3>{j.title}</h3>
            <p>{j.location}</p>
            <p>₹{j.payable_amount || j.wage}</p>
            <div className="actions">
              <Link className="btn ghost" to={"/jobs/" + j.id}>View</Link>
              {["Assigned","Ongoing"].includes(j.status) && <Link className="btn secondary" to={`/jobs/${j.id}/track`}>Track worker</Link>}
            </div>
          </div>
        ))}</div>
      )}
      <h2>Additional payment requests</h2>
      {extras.length === 0 ? <Empty title="No extra-work requests." text="Assigned workers can request extra pay if the job grows." /> : extras.map((x) => (
        <div className="card" key={x.id} style={{ marginBottom: 10 }}>
          <p>Job #{x.job_id} · ₹{x.amount} · <Badge>{x.status}</Badge></p>
          <p>{x.reason}</p>
          {x.status === "Pending" && <div className="actions"><button className="btn primary" onClick={() => extraStatus(x.id, "Accepted")}>Approve</button><button className="btn danger" onClick={() => extraStatus(x.id, "Rejected")}>Reject</button></div>}
        </div>
      ))}
    </div>
  );
}
