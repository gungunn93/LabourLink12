import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Badge, ErrorBox, Loading } from "../components/States";
import MapView from "../components/Map";
import ProfileModal from "../components/ProfileModal";

export default function JobDetails() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const toast = useToast();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [extra, setExtra] = useState({ amount: "", reason: "" });
  const [review, setReview] = useState({ rating: 5, comment: "" });
  const [workerId, setWorkerId] = useState(null);
  const [modal, setModal] = useState({ open: false, role: "employer", userId: null });

  const load = () => api.get("/jobs/" + id).then((r) => setD(r.data.data)).catch((e) => setErr(messageOf(e, "Job not found")));
  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    if (user?.role !== "employer") return;
    api.get("/applications").then((r) => {
      const hit = (r.data.data || []).find((x) => String(x.job?.id) === String(id) && ["Accepted", "Assigned", "Ongoing", "Completed"].includes(x.status));
      if (hit) setWorkerId(hit.worker.id);
    }).catch(() => {});
  }, [id, user]);

  const apply = async () => {
    try {
      await api.post("/jobs/" + id + "/apply", {});
      toast.success("Application submitted");
      load();
    } catch (e) { setErr(messageOf(e)); }
  };
  const extraReq = async () => {
    try {
      await api.post(`/jobs/${id}/extra-requests`, { amount: Number(extra.amount), reason: extra.reason });
      toast.success("Extra payment request sent");
    } catch (e) { setErr(messageOf(e)); }
  };
  const rate = async () => {
    try {
      await api.post("/ratings", {
        job_id: Number(id),
        reviewee_id: user.role === "worker" ? d.employer.id : workerId,
        rating: Number(review.rating),
        comment: review.comment,
      });
      toast.success("Review submitted");
    } catch (e) { setErr(messageOf(e)); }
  };

  if (err && !d) return <div className="page"><ErrorBox text={err} /></div>;
  if (!d) return <div className="page"><Loading /></div>;
  const j = d.job;
  return (
    <div className="page">
      <p className="crumbs"><Link to="/jobs">Jobs</Link> / {j.title}</p>
      <ErrorBox text={err} />
      <div className="card job-head">
        <div>
          <Badge>{j.status}</Badge>
          <h1>{j.title}</h1>
          <p>{j.description}</p>
          <p>{j.category} · {j.location} · {j.required_skills || "No specific skills"}</p>
          <p>Deadline {j.deadline || "Flexible"} · Duration {j.duration || "Not specified"}</p>
          {d.employer?.id && (
            <p>Posted by <button className="link-btn" data-testid="view-employer-profile" onClick={() => setModal({ open: true, role: "employer", userId: d.employer.id })}>{d.employer.name || "Employer"}</button></p>
          )}
        </div>
        <div>
          <div className="price">₹{j.payable_amount || j.wage}</div>
          <p>{j.payment_type} · extra ₹{j.extra_amount || 0}</p>
        </div>
      </div>
      {j.latitude && <div className="card" style={{ marginTop: 16 }}><MapView lat={j.latitude} lng={j.longitude} /></div>}
      <div className="actions">
        {user?.role === "worker" && j.status === "Open" && !d.already_applied && <button className="btn primary" onClick={apply}>Apply</button>}
        {user?.role === "worker" && d.already_applied && <span className="info">You have already applied.</span>}
        {j.is_negotiable && user && <button className="btn secondary" onClick={() => nav("/negotiation?job=" + j.id + "&worker=" + (user.role === "employer" ? "" : user.id))}>Negotiate pay</button>}
        {user && <button className="btn ghost" onClick={() => nav("/messages")}>Open chat</button>}
        {user && ["Assigned", "Ongoing"].includes(j.status) && <Link className="btn ghost" to={`/jobs/${j.id}/track`}>Live location</Link>}
      </div>
      {user?.role === "worker" && ["Assigned", "Ongoing"].includes(j.status) && (
        <div className="card form-card" style={{ marginTop: 16 }}>
          <h3>Request additional payment</h3>
          <input type="number" placeholder="Extra amount ₹" value={extra.amount} onChange={(e) => setExtra({ ...extra, amount: e.target.value })} />
          <textarea placeholder="Why is extra work required?" value={extra.reason} onChange={(e) => setExtra({ ...extra, reason: e.target.value })} />
          <button className="btn primary" onClick={extraReq}>Submit request</button>
        </div>
      )}
      {user && j.status === "Completed" && (
        <div className="card form-card" style={{ marginTop: 16 }}>
          <h3>Leave a rating</h3>
          <select value={review.rating} onChange={(e) => setReview({ ...review, rating: e.target.value })}>
            {[5,4,3,2,1].map((n) => <option key={n} value={n}>{n} stars</option>)}
          </select>
          <textarea placeholder="Comment" value={review.comment} onChange={(e) => setReview({ ...review, comment: e.target.value })} />
          <button className="btn primary" onClick={rate}>Submit review</button>
        </div>
      )}
      <ProfileModal open={modal.open} role={modal.role} userId={modal.userId} onClose={() => setModal({ ...modal, open: false })} />
    </div>
  );
}
