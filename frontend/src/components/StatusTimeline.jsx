import React from "react";

const STEPS = ["Pending", "Accepted", "Ongoing", "Completed"];

export default function StatusTimeline({ status }) {
  const current = STEPS.indexOf(status);
  return (
    <div className="timeline">
      {STEPS.map((step, i) => (
        <React.Fragment key={step}>
          <div className={`tl-step ${i < current ? "done" : i === current ? "active" : "future"}`}>
            <div className="tl-dot">{i < current ? "✓" : i + 1}</div>
            <span className="tl-label">{step}</span>
          </div>
          {i < STEPS.length - 1 && <div className={`tl-line ${i < current ? "done" : ""}`} />}
        </React.Fragment>
      ))}
    </div>
  );
}
