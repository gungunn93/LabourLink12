import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";
import { useToast } from "../context/ToastContext";
import ProfileModal from "../components/ProfileModal";

export default function Applications() {
  const { user } = useAuth();
  const isEmployer = user?.role === "employer";
  const toast = useToast();
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [hideBusy, setHideBusy] = useState(false);
  const [modal, setModal] = useState({ open: false, role: "worker", userId: null });
  const load = () => api.get("/applications").then((r) => setItems(r.data.data || [])).catch((e) => setErr(messageOf(e))).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const update = async (id, status) => {
    try { await api.put("/applications/" + id + "/status", { status }); toast.success("Updated"); load(); }
    catch (e) { setErr(messageOf(e)); }
  };
  const chat = async (a) => {
    try {
      await api.post("/conversations", { job_id: a.job.id, worker_id: a.worker.id, employer_id: a.job.employer_id });
      nav("/messages");
    } catch (e) { setErr(messageOf(e)); }
  };
  const openWorker = (id) => setModal({ open: true, role: "worker", userId: id });
  const openEmployer = (id) => setModal({ open: true, role: "employer", userId: id });

  const filtered = useMemo(() => (hideBusy ? items.filter((a) => !a.availability_conflict) : items), [items, hideBusy]);
  const busyCount = useMemo(() => items.filter((a) => a.availability_conflict).length, [items]);

  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <h1>Applications</h1>
      <ErrorBox text={err} />
      {isEmployer && busyCount > 0 && (
        <div className="filter-row" data-testid="busy-filter-row">
          <label className="toggle">
            <input
              type="checkbox"
              checked={hideBusy}
              onChange={(e) => setHideBusy(e.target.checked)}
              data-testid="hide-busy-checkbox"
            />
            <span>Hide workers busy on the job date ({busyCount})</span>
          </label>
        </div>
      )}
      {items.length === 0 ? <Empty title="No applications yet." text="Workers appear here after they apply." /> : filtered.length === 0 ? (
        <Empty title="All applicants are busy on this job's date." text="Turn off the filter to see them." />
      ) : (
        <div className="grid">{filtered.map((a) => {
          const busy = a.availability_conflict;
          const free = a.worker_availability === true;
          const cardCls = `card${busy && isEmployer ? " conflict" : ""}`;
          return (
            <div className={cardCls} key={a.id} data-testid={`application-card-${a.id}`}>
              <Badge>{a.status}</Badge>
              <h3>{a.job?.title}</h3>
              {a.worker && (
                <p>Worker: <button className="link-btn" data-testid={`worker-name-${a.worker.id}`} onClick={() => openWorker(a.worker.id)}>{a.worker.name}</button> · {a.worker.phone}</p>
              )}
              {isEmployer && a.job?.job_date && (
                <p className="muted" data-testid={`avail-line-${a.id}`}>
                  Job date: {new Date(a.job.job_date).toLocaleDateString()}
                  {busy && <span className="pill busy" data-testid={`busy-badge-${a.id}`}> · Busy on this date</span>}
                  {free && <span className="pill free" data-testid={`free-badge-${a.id}`}> · Available on this date</span>}
                  {a.worker_availability === null && <span className="muted"> · availability not set</span>}
                </p>
              )}
              {user?.role === "worker" && a.job?.employer_id && (
                <p>Employer: <button className="link-btn" data-testid={`employer-name-${a.job.employer_id}`} onClick={() => openEmployer(a.job.employer_id)}>View employer</button></p>
              )}
              <p>Agreed wage: ₹{a.agreed_wage || a.job?.wage}</p>
              <div className="actions">
                <Link className="btn ghost" to={"/jobs/" + a.job.id}>Job</Link>
                <button className="btn ghost" onClick={() => chat(a)}>Chat</button>
                <button className="btn ghost" onClick={() => nav(`/negotiation?job=${a.job.id}&worker=${a.worker?.id}`)}>Negotiate</button>
                {isEmployer && a.status === "Pending" && (
                  <>
                    <button
                      className="btn primary"
                      onClick={() => {
                        if (busy && !window.confirm("This worker is marked Busy on the job date. Accept anyway?")) return;
                        update(a.id, "Accepted");
                      }}
                      data-testid={`accept-${a.id}`}
                    >Accept</button>
                    <button className="btn danger" onClick={() => update(a.id, "Rejected")}>Reject</button>
                  </>
                )}
                {isEmployer && ["Accepted","Assigned"].includes(a.status) && (
                  <button className="btn secondary" onClick={() => update(a.id, "Ongoing")}>Mark ongoing</button>
                )}
              </div>
            </div>
          );
        })}</div>
      )}
      <ProfileModal open={modal.open} role={modal.role} userId={modal.userId} onClose={() => setModal({ ...modal, open: false })} />
    </div>
  );
}
