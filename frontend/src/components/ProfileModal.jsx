import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { ErrorBox, Loading } from "./States";
import ProfileView from "./ProfileView";

export default function ProfileModal({ role, userId, open, onClose }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !userId) return;
    setLoading(true);
    setErr("");
    setData(null);
    const url = role === "worker" ? `/workers/${userId}/public` : `/employers/${userId}/public`;
    api.get(url)
      .then((r) => setData(r.data.data))
      .catch((e) => setErr(messageOf(e, "Unable to load profile")))
      .finally(() => setLoading(false));
  }, [open, role, userId]);

  if (!open) return null;
  const routeBase = role === "worker" ? "/workers/" : "/employers/";
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" data-testid="profile-modal" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{role === "worker" ? "Worker profile" : "Employer profile"}</h3>
          <button className="btn ghost" onClick={onClose} data-testid="profile-modal-close" aria-label="Close">✕</button>
        </div>
        <div className="modal-body">
          {loading && <Loading />}
          <ErrorBox text={err} />
          {data && <ProfileView role={role} data={data} showShare={false} />}
        </div>
        {userId && (
          <div className="modal-foot">
            <Link className="btn primary" to={routeBase + userId} onClick={onClose} data-testid="profile-modal-view-full">View full profile</Link>
          </div>
        )}
      </div>
    </div>
  );
}
