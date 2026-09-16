import React from "react";

export function Loading({ text = "Loading..." }) {
  return (
    <div className="state">
      <div className="spinner" />
      <p>{text}</p>
    </div>
  );
}

export function Empty({ title, text }) {
  return (
    <div className="card empty">
      <h3>{title}</h3>
      <p>{text}</p>
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
