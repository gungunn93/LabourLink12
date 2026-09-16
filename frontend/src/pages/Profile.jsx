import React, { useEffect, useState } from "react";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../context/ToastContext";
import PortfolioManager from "../components/PortfolioManager";
import AvailabilityEditor from "../components/AvailabilityEditor";

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const endpoint = user?.role === "worker" ? "/workers/profile" : "/employers/profile";
  const [d, setD] = useState(null);
  const [f, setF] = useState({});
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(endpoint).then((r) => {
      setD(r.data.data);
      const p = r.data.data.profile || {};
      setF({
        name: r.data.data.user?.name || "",
        skills: p.skills || "",
        experience: p.experience || 0,
        location: p.location || "",
        availability: p.availability || "Available",
        languages: p.languages || "",
        company_name: p.company_name || "",
        about: p.about || "",
        employer_type: p.employer_type || "",
        latitude: p.latitude || "",
        longitude: p.longitude || "",
      });
    }).catch((e) => setErr(messageOf(e))).finally(() => setLoading(false));
  }, [endpoint]);

  const locate = () => navigator.geolocation.getCurrentPosition(
    (pos) => setF((s) => ({ ...s, latitude: pos.coords.latitude, longitude: pos.coords.longitude })),
    () => setErr("Location permission denied")
  );
  const save = async () => {
    try { await api.put(endpoint, f); toast.success("Profile updated"); }
    catch (e) { setErr(messageOf(e)); }
  };
  if (loading) return <div className="page"><Loading /></div>;
  return (
    <div className="page">
      <div className="card form-card">
        <h1>My profile</h1>
        <ErrorBox text={err} />
        <p data-testid="profile-contact">{d?.user?.email}{d?.user?.phone ? ` · ${d.user.phone}` : ""}</p>
        <div className="profile-reviews" data-testid="profile-reviews">
          <h3>Reviews · {d?.profile?.rating || 0}/5</h3>
          {(d?.reviews || []).length ? d.reviews.map((review) => <p key={`${review.date}-${review.reviewer}`}><b>{review.reviewer}</b> · {review.rating}/5 — {review.comment || "No comment"}</p>) : <p className="muted">No reviews yet.</p>}
        </div>
        <div className="form-grid">
          <label className="field"><span>Name</span><input value={f.name || ""} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
          <label className="field"><span>Location</span><input value={f.location || ""} onChange={(e) => setF({ ...f, location: e.target.value })} /></label>
          {user?.role === "worker" && (
            <>
              <label className="field"><span>Skills</span><input value={f.skills || ""} onChange={(e) => setF({ ...f, skills: e.target.value })} /></label>
              <label className="field"><span>Experience (years)</span><input type="number" value={f.experience || 0} onChange={(e) => setF({ ...f, experience: Number(e.target.value) })} /></label>
              <label className="field"><span>Availability</span><input value={f.availability || ""} onChange={(e) => setF({ ...f, availability: e.target.value })} /></label>
              <label className="field"><span>Languages</span><input value={f.languages || ""} onChange={(e) => setF({ ...f, languages: e.target.value })} /></label>
            </>
          )}
          {user?.role === "employer" && (
            <>
              <label className="field"><span>Company</span><input value={f.company_name || ""} onChange={(e) => setF({ ...f, company_name: e.target.value })} /></label>
              <label className="field"><span>Type</span><input value={f.employer_type || ""} onChange={(e) => setF({ ...f, employer_type: e.target.value })} /></label>
              <label className="field" style={{ gridColumn: "1 / -1" }}><span>About</span><textarea value={f.about || ""} onChange={(e) => setF({ ...f, about: e.target.value })} /></label>
            </>
          )}
        </div>
        <p>Coordinates: {f.latitude || "—"}, {f.longitude || "—"}</p>
        <div className="actions">
          <button className="btn ghost" onClick={locate}>Use browser location</button>
          <button className="btn primary" onClick={save}>Save profile</button>
        </div>
      </div>
      {user?.role === "worker" && (
        <div className="card form-card" style={{ marginTop: 16 }}>
          <AvailabilityEditor />
        </div>
      )}
      {user?.role === "worker" && (
        <div className="card form-card" style={{ marginTop: 16 }}>
          <PortfolioManager />
        </div>
      )}
    </div>
  );
}
