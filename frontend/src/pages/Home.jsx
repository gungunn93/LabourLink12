import React from "react";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="page" data-testid="home-page">
      <section className="hero">
        <div>
          <p className="eyebrow">SMART DAILY WAGE EMPLOYMENT</p>
          <h1>Hire nearby skilled workers. Get paid fairly for real work.</h1>
          <p>
            LabourLink is a marketplace for short-term jobs — painting, plumbing, electrical, carpentry and more.
            Workers apply, negotiate wages, chat, share live location on assigned jobs, and receive tracked payments.
          </p>
          <div className="actions">
            <Link className="btn primary" to="/register?role=worker">I am a worker</Link>
            <Link className="btn secondary" to="/register?role=employer">I need workers</Link>
            <Link className="btn ghost" to="/jobs">Browse open jobs</Link>
          </div>
        </div>
        <div className="hero-panel">
          <h2>Built for real job days</h2>
          <ul>
            <li>Email and password accounts</li>
            <li>Skill and distance-aware job matching</li>
            <li>Wage negotiation with offer history</li>
            <li>Chat, extra-work requests and ratings</li>
            <li>OpenStreetMap tracking for assigned jobs</li>
          </ul>
        </div>
      </section>
      <section className="features">
        <div className="card"><h3>Workers</h3><p>Find nearby jobs, apply, negotiate, share location while on an assigned job, and collect payments in your wallet.</p></div>
        <div className="card"><h3>Employers</h3><p>Post jobs with skills, pay and deadline. Review applications, chat, track assigned workers, and pay securely.</p></div>
        <div className="card"><h3>Admins</h3><p>Monitor users, jobs, applications, reports and transactions from a live operations dashboard.</p></div>
      </section>
    </div>
  );
}
