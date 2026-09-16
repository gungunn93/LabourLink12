import React, { useEffect, useState } from "react";
import api, { messageOf } from "../services/api";
import { useToast } from "../context/ToastContext";
import AvailabilityCalendar from "./AvailabilityCalendar";

export default function AvailabilityEditor() {
  const toast = useToast();
  const [days, setDays] = useState([]);
  const [dirty, setDirty] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/workers/availability")
      .then((r) => setDays(r.data.data || []))
      .catch((e) => setErr(messageOf(e)));
  }, []);

  const onChange = (next) => {
    const prev = days;
    const prevMap = new Map(prev.map((p) => [p.date, p.available]));
    const nextMap = new Map(next.map((p) => [p.date, p.available]));
    const changes = [];
    for (const [d, a] of nextMap) {
      if (prevMap.get(d) !== a) changes.push({ date: d, available: a });
    }
    for (const [d] of prevMap) {
      if (!nextMap.has(d)) changes.push({ date: d, remove: true });
    }
    setDays(next);
    setDirty(changes);
  };

  const save = async () => {
    if (dirty.length === 0) return;
    setBusy(true); setErr("");
    try {
      const r = await api.put("/workers/availability", { days: dirty });
      setDays(r.data.data || []);
      setDirty([]);
      toast.success("Availability saved");
    } catch (e) { setErr(messageOf(e)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="availability-editor">
      <h3>My availability</h3>
      <p className="muted">Mark the days you can work so employers only invite you when you're free.</p>
      {err && <div className="error">{err}</div>}
      <AvailabilityCalendar value={days} editable onChange={onChange} />
      <div className="actions" style={{ marginTop: 12 }}>
        <button
          className="btn primary"
          disabled={dirty.length === 0 || busy}
          onClick={save}
          data-testid="save-availability"
        >
          {busy ? "Saving…" : dirty.length ? `Save ${dirty.length} change${dirty.length > 1 ? "s" : ""}` : "Saved"}
        </button>
      </div>
    </div>
  );
}
