import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";
import { useToast } from "../context/ToastContext";

export default function Negotiation() {
  const { user } = useAuth();
  const toast = useToast();
  const [p] = useSearchParams();
  const job = p.get("job");
  const worker = p.get("worker");
  const [list, setList] = useState([]);
  const [active, setActive] = useState(null);
  const [offer, setOffer] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const loadList = async () => {
    try {
      const r = await api.get("/negotiations");
      setList(r.data.data || []);
    } catch (e) { setErr(messageOf(e)); }
    finally { setLoading(false); }
  };
  const open = async (id) => {
    const r = await api.get("/negotiations/" + id);
    setActive(r.data.data);
  };
  useEffect(() => { loadList(); }, []);

  const start = async () => {
    try {
      const body = { job_id: Number(job), offer: Number(offer) };
      if (user.role === "employer" && worker) body.worker_id = Number(worker);
      const r = await api.post("/negotiations", body);
      setActive(r.data.data);
      toast.success("Offer sent");
      loadList();
    } catch (e) { setErr(messageOf(e)); }
  };
  const counter = async () => {
    try {
      const r = await api.post("/negotiations/" + active.id + "/offer", { offer: Number(offer), message: "Counter offer" });
      setActive(r.data.data);
      setOffer("");
    } catch (e) { setErr(messageOf(e)); }
  };
  const act = async (kind) => {
    try {
      const r = await api.put(`/negotiations/${active.id}/${kind}`);
      setActive(r.data.data);
      toast.success(kind);
      loadList();
    } catch (e) { setErr(messageOf(e)); }
  };

  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <h1>Wage negotiation</h1>
      <ErrorBox text={err} />
      <div className="grid cols-2">
        <div className="card">
          <h3>Your threads</h3>
          {list.length === 0 && <Empty title="No negotiations yet." text="Open a job and send an offer." />}
          {list.map((n) => (
            <button className="conversation" key={n.id} onClick={() => open(n.id)}>
              {n.job?.title} · ₹{n.current_offer} · {n.status}
            </button>
          ))}
          {job && (
            <div className="form-card" style={{ marginTop: 16 }}>
              <h3>New offer for job #{job}</h3>
              <input type="number" value={offer} onChange={(e) => setOffer(e.target.value)} placeholder="Offer ₹" />
              <button className="btn primary" onClick={start}>Send initial offer</button>
            </div>
          )}
        </div>
        <div className="card">
          {!active ? <p>Select a negotiation to view history.</p> : (
            <>
              <Badge>{active.status}</Badge>
              <p>Original: ₹{active.original_price} · Current: ₹{active.current_offer}</p>
              <p>Suggested fair wage: ₹{active.suggested_wage}</p>
              <div className="messages">
                {(active.history || []).map((m, i) => (
                  <div key={i} className={`bubble ${m.sender_id === user.id ? "mine" : "theirs"}`}>
                    {m.action} · ₹{m.offer}<br />{m.message}<br /><small>{m.date}</small>
                  </div>
                ))}
              </div>
              {["Pending","Countered"].includes(active.status) && (
                <>
                  <input type="number" value={offer} onChange={(e) => setOffer(e.target.value)} placeholder="Counter offer ₹" />
                  <div className="actions">
                    <button className="btn secondary" onClick={counter}>Counter</button>
                    <button className="btn primary" onClick={() => act("accept")}>Accept</button>
                    <button className="btn danger" onClick={() => act("reject")}>Reject</button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
