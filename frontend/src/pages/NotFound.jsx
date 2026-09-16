import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page">
      <div className="card empty">
        <h1>Page not found</h1>
        <p>That route does not exist.</p>
        <Link className="btn primary" to="/">Back to home</Link>
      </div>
    </div>
  );
}
