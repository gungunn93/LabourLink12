import React, { useMemo, useState } from "react";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function toISO(d) {
  const yr = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${yr}-${mo}-${day}`;
}

function startOfMonth(anchor) { return new Date(anchor.getFullYear(), anchor.getMonth(), 1); }

function buildGrid(anchor) {
  const first = startOfMonth(anchor);
  const startDow = first.getDay();
  const daysInMonth = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0).getDate();
  const grid = [];
  for (let i = 0; i < startDow; i++) grid.push(null);
  for (let d = 1; d <= daysInMonth; d++) grid.push(new Date(anchor.getFullYear(), anchor.getMonth(), d));
  while (grid.length % 7 !== 0) grid.push(null);
  return grid;
}

export default function AvailabilityCalendar({
  value = [],           // [{date, available}]
  editable = false,
  onChange,             // (nextArray) => void
  monthAnchor,          // Date optional
}) {
  const [anchor, setAnchor] = useState(monthAnchor || new Date());
  const grid = useMemo(() => buildGrid(anchor), [anchor]);
  const map = useMemo(() => {
    const m = new Map();
    for (const v of value || []) m.set(v.date, v.available);
    return m;
  }, [value]);
  const today = toISO(new Date());

  const toggle = (iso, isPast) => {
    if (!editable || isPast) return;
    const current = map.get(iso);
    const list = (value || []).filter((v) => v.date !== iso);
    // cycle: undefined -> true (available) -> false (busy) -> undefined
    if (current === undefined) list.push({ date: iso, available: true });
    else if (current === true) list.push({ date: iso, available: false });
    // if false, drop (remove marker)
    onChange && onChange(list);
  };

  const changeMonth = (delta) => {
    const next = new Date(anchor.getFullYear(), anchor.getMonth() + delta, 1);
    setAnchor(next);
  };

  const monthLabel = anchor.toLocaleString(undefined, { month: "long", year: "numeric" });

  return (
    <div className="cal-wrap" data-testid="availability-calendar">
      <div className="cal-head">
        <button className="btn ghost" onClick={() => changeMonth(-1)} data-testid="cal-prev" aria-label="Previous month">‹</button>
        <div className="cal-title" data-testid="cal-title">{monthLabel}</div>
        <button className="btn ghost" onClick={() => changeMonth(1)} data-testid="cal-next" aria-label="Next month">›</button>
      </div>
      <div className="cal-grid cal-dow">
        {DAY_LABELS.map((d) => <div key={d} className="cal-dow-cell">{d}</div>)}
      </div>
      <div className="cal-grid">
        {grid.map((d, i) => {
          if (!d) return <div key={`e${i}`} className="cal-cell empty" />;
          const iso = toISO(d);
          const status = map.get(iso);
          const isPast = iso < today;
          const cls = ["cal-cell"];
          if (status === true) cls.push("free");
          if (status === false) cls.push("busy");
          if (isPast) cls.push("past");
          if (iso === today) cls.push("today");
          return (
            <button
              key={iso}
              type="button"
              className={cls.join(" ")}
              disabled={!editable || isPast}
              onClick={() => toggle(iso, isPast)}
              data-testid={`cal-day-${iso}`}
              aria-label={`${iso} ${status === true ? "available" : status === false ? "busy" : "not set"}`}
            >
              <span className="cal-day-num">{d.getDate()}</span>
              {status === true && <span className="cal-dot free" />}
              {status === false && <span className="cal-dot busy" />}
            </button>
          );
        })}
      </div>
      <div className="cal-legend">
        <span><span className="cal-dot free" /> Available</span>
        <span><span className="cal-dot busy" /> Busy</span>
        {editable && <span className="muted">Tap a day to cycle: available → busy → clear</span>}
      </div>
    </div>
  );
}
