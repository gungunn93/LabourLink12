import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { Empty, ErrorBox, Loading, Badge } from "../components/States";

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

  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <h1>Worker dashboard</h1>
      <ErrorBox text={err} />
      <div className="stats">
        <div className="card stat"><b>Wallet</b><strong>₹{earn?.wallet?.balance || 0}</strong></div>
        <div className="card stat"><b>Total earned</b><strong>₹{earn?.wallet?.total_earnings || 0}</strong></div>
        <div className="card stat"><b>Matched jobs</b><strong>{jobs.length}</strong></div>
        <div className="card stat"><b>Assigned / ongoing</b><strong>{assigned.filter((x) => x.status !== "Completed").length}</strong></div>
      </div>
      <h2>Your jobs</h2>
      {assigned.length === 0 ? <Empty title="No assigned jobs yet." text="Apply to an open job to get started." /> : (
        <div className="grid cols-2">{assigned.map((a) => (
          <div className="card" key={a.id}>
            <Badge>{a.status}</Badge>
            <h3>{a.job?.title}</h3>
            <p>₹{a.agreed_wage || a.job?.wage}</p>
            <Link className="btn ghost" to={"/jobs/" + a.job.id}>Open</Link>
            {["Accepted","Assigned","Ongoing"].includes(a.status) && <Link className="btn secondary" to={`/jobs/${a.job.id}/track`}>Share location</Link>}
          </div>
        ))}</div>
      )}
      <h2>Recommended near you</h2>
      {jobs.length === 0 ? <Empty title="No jobs available in your area right now." text="Update your skills and location in Profile." /> : (
        <div className="grid cols-3">{jobs.slice(0, 9).map((j) => (
          <div className="card" key={j.id}>
            <h3>{j.title}</h3>
            <p>{j.location}</p>
            <p>Match {j.match_score} · ₹{j.wage}</p>
            <Link className="btn ghost" to={"/jobs/" + j.id}>View</Link>
          </div>
        ))}</div>
      )}
    </div>
  );
}
