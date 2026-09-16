import React from "react";

export function Loading({ text = "Loading..." }) {
  return (
    <div className="state">
      <div className="spinner" />
      <p>{text}</p>
    </div>
  );
}

/** Skeleton card — grey animated placeholder while content loads */
export function CardSkeleton() {
  return (
    <div className="card skeleton-card">
      <div className="skel skel-badge" />
      <div className="skel skel-title" />
      <div className="skel skel-line" />
      <div className="skel skel-line short" />
      <div className="skel skel-price" />
      <div className="skel skel-btn" />
    </div>
  );
}

/** Improved empty state with optional icon */
export function Empty({ title, text, icon }) {
  return (
    <div className="card empty">
      {icon && <div className="empty-icon">{icon}</div>}
      <h3>{title}</h3>
      {text && <p>{text}</p>}
    </div>
  );
}

export function ErrorBox({ text }) {
  if (!text) return null;
  return <div className="error">{text}</div>;
}

export function Badge({ children }) {
  const key = String(children || "").toLowerCase();
  return <span className={`badge ${key}`}>{children}</span>;
}
