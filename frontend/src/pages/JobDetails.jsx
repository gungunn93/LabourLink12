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
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [workerId, setWorkerId] = useState(null);
  const [modal, setModal] = useState({ open: false, role: "employer", userId: null });

  const load = () => api.get("/jobs/" + id).then((r) => {
    const data = r.data.data;
    setD(data);
    // Auto-show rating prompt if job just completed and user hasn't rated yet
    if (data?.job?.status === "Completed") {
      api.get("/ratings?job_id=" + id).then((rr) => {
        const ratings = rr.data.data || [];
        const alreadyRated = ratings.some((r) => r.reviewer_id === user?.id);
        if (!alreadyRated) setShowRatingModal(true);
      }).catch(() => {});
    }
  }).catch((e) => setErr(messageOf(e, "Job not found")));
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
      setShowRatingModal(false);
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

      {/* Rating prompt modal — auto-shows when job is completed */}
      {showRatingModal && user && (
        <div className="modal-overlay" role="dialog" aria-modal="true">
          <div className="modal-panel">
            <div className="modal-head">
              <h3>⭐ Rate this job</h3>
              <button className="btn ghost" onClick={() => setShowRatingModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: 16, color: "var(--muted)" }}>
                {user.role === "worker"
                  ? "How was working with this employer?"
                  : "How was this worker's performance?"}
              </p>
              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setReview({ ...review, rating: n })}
                    style={{
                      fontSize: 28, background: "none", border: "none", cursor: "pointer",
                      color: n <= review.rating ? "#f2b41a" : "#d0d6d5",
                    }}
                    aria-label={`${n} star`}
                  >★</button>
                ))}
              </div>
              <textarea
                placeholder="Write a comment (optional)"
                value={review.comment}
                onChange={(e) => setReview({ ...review, comment: e.target.value })}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 12, border: "1px solid var(--line)", minHeight: 80 }}
              />
            </div>
            <div className="modal-foot" style={{ gap: 10, display: "flex", justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setShowRatingModal(false)}>Skip</button>
              <button className="btn primary" onClick={rate}>Submit rating</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
