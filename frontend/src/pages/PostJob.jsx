import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useToast } from "../context/ToastContext";
import { ErrorBox } from "../components/States";

const CATS = ["Painting","Plumbing","Electrical","Carpentry","Cleaning","Masonry","Construction","Gardening","Moving","Other"];

export default function PostJob() {
  const nav = useNavigate();
  const toast = useToast();
  const [f, setF] = useState({
    title: "", description: "", category: "Painting", location: "", wage: "",
    payment_type: "daily", required_workers: 1, job_date: "", deadline: "",
    required_skills: "", duration: "", is_negotiable: true, image: "",
    notify_radius_km: 25,
  });
  const [err, setErr] = useState("");
  const up = (e) => setF({ ...f, [e.target.name]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const locate = () => {
    if (!navigator.geolocation) return setErr("Geolocation is not supported");
    navigator.geolocation.getCurrentPosition(
      (pos) => setF((s) => ({ ...s, latitude: pos.coords.latitude, longitude: pos.coords.longitude })),
      () => setErr("Location permission denied. You can still post without coordinates.")
    );
  };

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const r = await api.post("/upload", body);
      setF((s) => ({ ...s, image: r.data.data.url }));
    } catch (error) {
      setErr(messageOf(error, "Upload failed"));
    }
  };

  const save = async (e) => {
    e.preventDefault();
    try {
      const r = await api.post("/jobs", {
        ...f,
        wage: Number(f.wage),
        required_workers: Number(f.required_workers),
        notify_radius_km: Number(f.notify_radius_km) || 25,
      });
      const notified = r?.data?.data?.notified_workers ?? 0;
      const radius = r?.data?.data?.notify_radius_km ?? f.notify_radius_km;
      toast.success(
        notified > 0
          ? `Job posted · notified ${notified} worker${notified === 1 ? "" : "s"} within ${radius} km`
          : "Job posted"
      );
      nav("/employer/dashboard");
    } catch (error) {
      setErr(messageOf(error, "Unable to post job"));
    }
  };

  return (
    <div className="page">
      <p className="crumbs">Employer / Post job</p>
      <form className="card form-card" onSubmit={save}>
        <h1>Post a job</h1>
        <ErrorBox text={err} />
        <div className="form-grid">
          <label className="field"><span>Title</span><input name="title" onChange={up} required /></label>
          <label className="field"><span>Category</span><select name="category" value={f.category} onChange={up}>{CATS.map((x) => <option key={x}>{x}</option>)}</select></label>
          <label className="field"><span>Location</span><input name="location" onChange={up} required /></label>
          <label className="field"><span>Wage ₹</span><input name="wage" type="number" onChange={up} required /></label>
          <label className="field"><span>Payment type</span><select name="payment_type" value={f.payment_type} onChange={up}><option value="daily">Daily</option><option value="fixed">Fixed</option><option value="hourly">Hourly</option></select></label>
          <label className="field"><span>Workers needed</span><input name="required_workers" type="number" min="1" value={f.required_workers} onChange={up} /></label>
          <label className="field"><span>Job date</span><input name="job_date" type="date" onChange={up} /></label>
          <label className="field"><span>Deadline</span><input name="deadline" type="date" onChange={up} /></label>
          <label className="field"><span>Required skills</span><input name="required_skills" onChange={up} /></label>
          <label className="field"><span>Duration</span><input name="duration" onChange={up} /></label>
          <label className="field">
            <span>Notify workers within (km)</span>
            <input
              name="notify_radius_km"
              type="number"
              min="1"
              max="100"
              step="1"
              value={f.notify_radius_km}
              onChange={up}
              data-testid="notify-radius-input"
            />
          </label>
        </div>
        <label className="field"><span>Description</span><textarea name="description" onChange={up} rows={5} /></label>
        <label className="field"><span>Job image</span><input type="file" accept="image/*" onChange={upload} /></label>
        <label><input type="checkbox" name="is_negotiable" checked={f.is_negotiable} onChange={up} /> Allow wage negotiation</label>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={locate}>Use my location</button>
          <button className="btn primary">Publish job</button>
        </div>
      </form>
    </div>
  );
}
