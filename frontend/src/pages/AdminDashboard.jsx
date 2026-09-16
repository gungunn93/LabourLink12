import React, { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { messageOf } from "../services/api";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";

export default function AdminDashboard() {
  const [tab, setTab] = useState("overview");
  const [d, setD] = useState(null);
  const [users, setUsers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [pays, setPays] = useState([]);
  const [reports, setReports] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/admin/dashboard"),
      api.get("/admin/users"),
      api.get("/admin/jobs"),
      api.get("/admin/applications"),
      api.get("/admin/payments"),
      api.get("/admin/reports"),
    ]).then(([a,b,c,d2,e,f]) => {
      setD(a.data.data); setUsers(b.data.data||[]); setJobs(c.data.data||[]);
      setApps(d2.data.data||[]); setPays(e.data.data||[]); setReports(f.data.data||[]);
    }).catch((e) => setErr(messageOf(e, "Admin access required"))).finally(() => setLoading(false));
  }, []);

  const toggle = async (u) => {
    await api.put(`/admin/users/${u.id}/status`, { active: !u.active });
    setUsers((list) => list.map((x) => x.id === u.id ? { ...x, active: !x.active } : x));
  };
  const resolve = async (id) => { await api.put(`/admin/reports/${id}`, { status: "Reviewed" }); setReports((list) => list.map((r) => r.id === id ? { ...r, status: "Reviewed" } : r)); };

  if (loading) return <div className="page"><Loading /></div>;
  const chart = [
    { name: "Users", v: d?.users || 0 },
    { name: "Jobs", v: d?.jobs || 0 },
    { name: "Apps", v: d?.applications || 0 },
    { name: "Paid", v: d?.transactions || 0 },
  ];
  return (
    <div className="page page-wide">
      <h1>Admin operations</h1>
      <ErrorBox text={err} />
      <div className="actions">
        {["overview","users","jobs","applications","transactions","reports"].map((t) => (
          <button key={t} className={`btn ${tab===t?"primary":"ghost"}`} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      {tab === "overview" && d && (
        <>
          <div className="stats">
            {Object.entries(d).map(([k,v]) => <div className="card stat" key={k}><b>{k.replaceAll("_"," ")}</b><strong>{typeof v === "number" ? (String(k).includes("revenue") || String(k).includes("fee") ? `₹${v}` : v) : v}</strong></div>)}
          </div>
          <div className="card" style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="v" fill="#0b4f52" radius={8} /></BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
      {tab === "users" && (
        <div className="card table-wrap">
          <table><thead><tr><th>Name</th><th>Role</th><th>Phone</th><th>Verified</th><th>Status</th><th></th></tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id}><td>{u.name}<br /><small>{u.email}</small></td><td>{u.role}</td><td>{u.phone}</td><td>{u.otp_verified ? "Yes" : "No"}</td><td><Badge>{u.active ? "active" : "blocked"}</Badge></td>
              <td>{u.role !== "admin" && <button className="btn ghost" onClick={() => toggle(u)}>{u.active ? "Block" : "Unblock"}</button>}</td></tr>
            ))}</tbody></table>
        </div>
      )}
      {tab === "jobs" && (jobs.length === 0 ? <Empty title="No jobs." /> : jobs.map((j) => <div className="card" key={j.id}><b>{j.title}</b> · {j.status} · ₹{j.wage}</div>))}
      {tab === "applications" && (apps.length === 0 ? <Empty title="No applications." /> : <div className="card table-wrap"><table><thead><tr><th>ID</th><th>Job</th><th>Worker</th><th>Status</th></tr></thead><tbody>{apps.map((a)=><tr key={a.id}><td>{a.id}</td><td>{a.job_id}</td><td>{a.worker_id}</td><td>{a.status}</td></tr>)}</tbody></table></div>)}
      {tab === "transactions" && (pays.length === 0 ? <Empty title="No transactions." /> : pays.map((p) => <div className="card" key={p.id}>{p.reference_id} · ₹{p.amount} · {p.status}</div>))}
      {tab === "reports" && (reports.length === 0 ? <Empty title="No reports." text="User-submitted issues will appear here." /> : reports.map((r) => (
        <div className="card" key={r.id}><p>{r.target_type} #{r.target_id} · <Badge>{r.status}</Badge></p><p>{r.reason}</p>{r.status==="Open" && <button className="btn ghost" onClick={() => resolve(r.id)}>Mark reviewed</button>}</div>
      )))}
    </div>
  );
}
