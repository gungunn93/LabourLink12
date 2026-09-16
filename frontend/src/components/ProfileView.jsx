import React, { useState } from "react";
import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import AvailabilityCalendar from "./AvailabilityCalendar";

function Stars({ value = 0 }) {
  const full = Math.round(value);
  return (
    <span className="stars" aria-label={`${value} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= full ? "star on" : "star"}>★</span>
      ))}
    </span>
  );
}

export function RatingBreakdown({ rating }) {
  if (!rating) return null;
  const total = rating.count || 0;
  return (
    <div className="rating-summary" data-testid="rating-summary">
      <div className="rating-score">
        <div className="rating-avg" data-testid="rating-avg">{Number(rating.average || 0).toFixed(1)}</div>
        <Stars value={rating.average || 0} />
        <div className="rating-count muted">{total} review{total === 1 ? "" : "s"}</div>
      </div>
      <div className="rating-bars">
        {(rating.breakdown || []).map((b) => {
          const pct = total ? Math.round((b.count / total) * 100) : 0;
          return (
            <div key={b.stars} className="rating-bar-row">
              <span className="rating-bar-label">{b.stars}★</span>
              <div className="rating-bar-track"><div className="rating-bar-fill" style={{ width: `${pct}%` }} /></div>
              <span className="rating-bar-count muted">{b.count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ReviewList({ reviews }) {
  if (!reviews || reviews.length === 0) return <p className="muted" data-testid="no-reviews">No reviews yet.</p>;
  return (
    <ul className="review-list" data-testid="review-list">
      {reviews.map((r, i) => (
        <li key={`${r.date}-${i}`} className="review-item">
          <div className="review-head">
            <b>{r.reviewer}</b>
            <Stars value={r.rating} />
            {r.date && <span className="muted">· {new Date(r.date).toLocaleDateString()}</span>}
          </div>
          <div className="review-meta">
            {r.verified && (
              <span className="verified-badge" data-testid="verified-badge" title="Verified: this reviewer completed the job">
                <span className="verified-tick">✓</span> Verified{r.job_title ? ` · ${r.job_title}` : ""}
              </span>
            )}
            {!r.verified && r.job_title && <span className="muted">Job: {r.job_title}</span>}
          </div>
          {r.comment && <p className="review-comment">{r.comment}</p>}
        </li>
      ))}
    </ul>
  );
}

export function PortfolioGrid({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h3>Past work</h3>
      <div className="portfolio-grid" data-testid="portfolio-grid">
        {items.map((item) => (
          <figure key={item.id} className="portfolio-item">
            <img src={item.image_url} alt={item.caption || "Past work"} loading="lazy" />
            {item.caption && <figcaption>{item.caption}</figcaption>}
          </figure>
        ))}
      </div>
    </div>
  );
}

export function ShareProfile({ role, userId }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const url = `${window.location.origin}/${role === "worker" ? "workers" : "employers"}/${userId}`;
  const waLink = `https://wa.me/?text=${encodeURIComponent(`Check my LabourLink profile: ${url}`)}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      const el = document.createElement("input");
      el.value = url; document.body.appendChild(el); el.select();
      document.execCommand("copy"); document.body.removeChild(el);
      setCopied(true); setTimeout(() => setCopied(false), 1800);
    }
  };
  return (
    <div className="share-row">
      <button className="btn ghost" data-testid="share-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? "Hide share options" : "Share profile"}
      </button>
      {open && (
        <div className="share-panel" data-testid="share-panel">
          <div className="share-actions">
            <input className="share-url" value={url} readOnly data-testid="share-url" />
            <button className="btn primary" onClick={copy} data-testid="copy-link">{copied ? "Copied!" : "Copy link"}</button>
            <a className="btn secondary" href={waLink} target="_blank" rel="noreferrer" data-testid="share-whatsapp">WhatsApp</a>
          </div>
          <div className="share-qr" data-testid="share-qr">
            <QRCodeSVG value={url} size={140} includeMargin bgColor="#ffffff" fgColor="#0b4f52" />
            <p className="muted">Scan to open this profile</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProfileView({ role, data, showShare = true }) {
  if (!data) return null;
  const p = data.profile || {};
  const isWorker = role === "worker";
  return (
    <div className="profile-view" data-testid={`public-profile-${role}`}>
      <div className="profile-head">
        <div className="profile-avatar">{(data.user?.name || "?").slice(0, 1).toUpperCase()}</div>
        <div>
          <h2 data-testid="profile-name">{data.user?.name}</h2>
          <p className="muted">
            {isWorker
              ? `${p.skills || "Skilled worker"} · ${p.experience || 0} yrs exp · ${p.location || "Location unavailable"}`
              : `${p.company_name || "Employer"} · ${p.employer_type || ""} · ${p.location || ""}`}
          </p>
          <p className="muted">
            {isWorker
              ? `Availability: ${p.availability || "—"} · Completed jobs: ${p.completed_jobs || 0}`
              : `Jobs posted: ${p.jobs_posted || 0} · Workers hired: ${p.workers_hired || 0}`}
          </p>
        </div>
      </div>
      {!isWorker && p.about && <p className="profile-about">{p.about}</p>}
      {isWorker && p.languages && <p className="muted">Languages: {p.languages}</p>}
      {showShare && data.user?.id && <ShareProfile role={role} userId={data.user.id} />}
      <RatingBreakdown rating={data.rating} />
      {isWorker && data.availability_days && data.availability_days.length > 0 && (
        <div data-testid="availability-public">
          <h3>Availability</h3>
          <AvailabilityCalendar value={data.availability_days} editable={false} />
        </div>
      )}
      {isWorker && <PortfolioGrid items={data.portfolio} />}
      <h3>Reviews</h3>
      <ReviewList reviews={data.reviews} />
    </div>
  );
}
