import React, { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useSocket } from "../context/SocketContext";
import MapView from "../components/Map";
import { ErrorBox, Loading } from "../components/States";

export default function TrackJob() {
  const { id } = useParams();
  const { user } = useAuth();
  const socket = useSocket();
  const [loc, setLoc] = useState(null);
  const [err, setErr] = useState("");
  const [sharing, setSharing] = useState(false);
  const timer = useRef(null);

  const load = async () => {
    try {
      const r = await api.get(`/jobs/${id}/location`);
      setLoc(r.data.data);
    } catch (e) { setErr(messageOf(e)); }
  };
  useEffect(() => { load(); }, [id]);
  useEffect(() => {
    if (!socket) return;
    socket.emit("join_job_location", { job_id: Number(id), auth: { token: localStorage.getItem("ll_token") } });
    const handler = (payload) => { if (String(payload.job_id) === String(id)) setLoc(payload); };
    socket.on("location:update", handler);
    return () => socket.off("location:update", handler);
  }, [socket, id]);

  const send = async (path, coords) => {
    await api.post(`/jobs/${id}/location/${path}`, {
      latitude: coords.latitude,
      longitude: coords.longitude,
      accuracy: coords.accuracy,
    });
  };
  const start = () => {
    if (!navigator.geolocation) return setErr("Geolocation is not supported in this browser");
    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        await send("start", pos.coords);
        setSharing(true);
        timer.current = setInterval(() => {
          navigator.geolocation.getCurrentPosition((p) => send("update", p.coords).catch(() => {}), () => {}, { enableHighAccuracy: true });
        }, 12000);
      } catch (e) { setErr(messageOf(e)); }
    }, () => setErr("Location permission denied. Enable location to share with the employer."));
  };
  const stop = async () => {
    clearInterval(timer.current);
    setSharing(false);
    try { await api.post(`/jobs/${id}/location/stop`); } catch (e) { setErr(messageOf(e)); }
  };
  useEffect(() => () => clearInterval(timer.current), []);

  if (!loc && !err) return <div className="page"><Loading /></div>;
  const lat = loc?.job_latitude ?? loc?.latitude;
  const lng = loc?.job_longitude ?? loc?.longitude;
  return (
    <div className="page">
      <h1>Live job location</h1>
      <p>Location is available only for assigned jobs, and only while the worker chooses to share it.</p>
      <ErrorBox text={err} />
      <div className="card">
        {lat != null && lng != null ? <MapView lat={lat} lng={lng} worker={loc?.latitude != null ? loc : null} height={360} /> : <div className="info" data-testid="location-not-available">No map coordinates are available for this assigned job yet.</div>}
        <p data-testid="location-sharing-status">{loc?.is_active ? "Sharing is active" : "Worker is not sharing right now"} {loc?.updated_at && `· updated ${loc.updated_at}`}</p>
        {user?.role === "worker" && (
          <div className="actions">
            {!sharing ? <button data-testid="location-start-button" className="btn primary" onClick={start}>Start sharing</button> : <button data-testid="location-stop-button" className="btn danger" onClick={stop}>Stop sharing</button>}
          </div>
        )}
      </div>
    </div>
  );
}
