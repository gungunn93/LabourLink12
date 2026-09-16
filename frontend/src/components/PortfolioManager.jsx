import React, { useEffect, useRef, useState } from "react";
import api, { messageOf } from "../services/api";
import { useToast } from "../context/ToastContext";

export default function PortfolioManager() {
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const fileRef = useRef(null);

  const load = () => api.get("/workers/portfolio").then((r) => setItems(r.data.data || [])).catch((e) => setErr(messageOf(e)));
  useEffect(() => { load(); }, []);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setErr("");
    try {
      const form = new FormData();
      form.append("file", file);
      const up = await api.post("/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
      await api.post("/workers/portfolio", { image_url: up.data.data.url, caption });
      setCaption("");
      if (fileRef.current) fileRef.current.value = "";
      toast.success("Photo added");
      load();
    } catch (ex) { setErr(messageOf(ex)); }
    finally { setBusy(false); }
  };

  const remove = async (id) => {
    try { await api.delete(`/workers/portfolio/${id}`); load(); }
    catch (ex) { setErr(messageOf(ex)); }
  };

  return (
    <div className="portfolio-manager" data-testid="portfolio-manager">
      <h3>Past work photos</h3>
      <p className="muted">Show employers photos of jobs you've completed.</p>
      {err && <div className="error">{err}</div>}
      <div className="portfolio-upload">
        <input
          placeholder="Caption (optional)"
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          data-testid="portfolio-caption"
        />
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={onFile}
          disabled={busy}
          data-testid="portfolio-file"
        />
      </div>
      {items.length === 0 ? <p className="muted">No photos yet.</p> : (
        <div className="portfolio-grid">
          {items.map((it) => (
            <figure key={it.id} className="portfolio-item">
              <img src={it.image_url} alt={it.caption || "Past work"} loading="lazy" />
              {it.caption && <figcaption>{it.caption}</figcaption>}
              <button className="btn danger portfolio-remove" onClick={() => remove(it.id)} data-testid={`portfolio-remove-${it.id}`}>Remove</button>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
