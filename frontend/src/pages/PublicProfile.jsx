import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { ErrorBox, Loading } from "../components/States";
import ProfileView from "../components/ProfileView";

export default function PublicProfile({ role }) {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setErr("");
    const url = role === "worker" ? `/workers/${id}/public` : `/employers/${id}/public`;
    api.get(url)
      .then((r) => setData(r.data.data))
      .catch((e) => setErr(messageOf(e, "Profile not found")))
      .finally(() => setLoading(false));
  }, [id, role]);

  return (
    <div className="page" data-testid={`public-profile-page-${role}`}>
      <p className="crumbs"><Link to="/">Home</Link> / {role === "worker" ? "Workers" : "Employers"} / #{id}</p>
      {loading ? <Loading /> : err ? <ErrorBox text={err} /> : (
        <div className="card">
          <ProfileView role={role} data={data} />
        </div>
      )}
    </div>
  );
}
