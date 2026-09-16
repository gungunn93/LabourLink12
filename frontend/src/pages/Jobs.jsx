import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Badge, Empty, ErrorBox, Loading, CardSkeleton } from "../components/States";

export default function Jobs() {
  const { user, token } = useAuth();
  const toast = useToast();
  const isWorker = user?.role === "worker";
  const [jobs, setJobs] = useState([]);
  const [cats, setCats] = useState([]);
  const [saved, setSaved] = useState(new Set());
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [date, setDate] = useState("");
  const [minWage, setMinWage] = useState("");
  const [maxWage, setMaxWage] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setErr("");
    setLoading(true);
    try {
      const params = { q, category, sort };
      if (date) params.date = date;
      if (minWage) params.min_wage = minWage;
      if (maxWage) params.max_wage = maxWage;
      if (availableOnly && isWorker) params.available_only = "true";
      const r = await api.get("/jobs", { params });
      setJobs(r.data.data || []);
    } catch (e) {
      setErr(messageOf(e, "Unable to load jobs"));
    } finally {
      setLoading(false);
    }
  };

  const loadSaved = async () => {
    if (!token) return;
    try {
      const r = await api.get("/jobs/saved");
      setSaved(new Set((r.data.data || []).map((j) => j.id)));
    } catch (_) {}
  };

  useEffect(() => {
    api.get("/categories").then((r) => setCats(r.data.data || [])).catch(() => {});
    load();
    loadSaved();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [availableOnly, date]);

  const toggleSave = async (jobId, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!token) { toast.error("Please login to save jobs"); return; }
    try {
      const r = await api.post(`/jobs/${jobId}/save`);
      const isSaved = r.data.data?.saved;
      setSaved((prev) => {
        const next = new Set(prev);
        isSaved ? next.add(jobId) : next.delete(jobId);
        return next;
      });
      toast.success(isSaved ? "Job saved!" : "Job removed from saved");
    } catch (e) { toast.error(messageOf(e)); }
  };

  const clearFilters = () => {
    setQ(""); setCategory(""); setSort("newest"); setDate("");
    setMinWage(""); setMaxWage(""); setAvailableOnly(false);
    queueMicrotask(() => {
      api.get("/jobs", { params: { q: "", category: "", sort: "newest" } })
        .then((r) => setJobs(r.data.data || []))
        .catch((e) => setErr(messageOf(e, "Unable to load jobs")));
    });
  };

  const displayJobs = showSaved ? jobs.filter((j) => saved.has(j.id)) : jobs;
  const hasFilters = q || category || date || minWage || maxWage || availableOnly || sort !== "newest";

  return (
    <div className="page">
      <p className="crumbs">Home / Jobs</p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <h1 style={{ margin: 0 }}>Find nearby work</h1>
        {token && (
          <button
            className={`btn ${showSaved ? "primary" : "ghost"}`}
            onClick={() => setShowSaved(!showSaved)}
          >
            {showSaved ? "★ Saved jobs" : "☆ Saved jobs"} {saved.size > 0 && `(${saved.size})`}
          </button>
        )}
      </div>

      {/* Search & filters */}
      <div className="search-row" style={{ marginTop: 16 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, skill or area" data-testid="jobs-search-input" style={{ flex: 2 }} />
        <select value={category} onChange={(e) => setCategory(e.target.value)} data-testid="jobs-category-select">
          <option value="">All categories</option>
          {cats.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} data-testid="jobs-sort-select">
          <option value="newest">Newest</option>
          <option value="wage">Highest wage</option>
          <option value="nearest">Nearest</option>
        </select>
        <button className="btn primary" onClick={load} data-testid="jobs-search-btn">Search</button>
      </div>

      {/* Wage range + date filters */}
      <div className="search-row">
        <input
          type="number"
          placeholder="Min wage ₹"
          value={minWage}
          onChange={(e) => setMinWage(e.target.value)}
          style={{ width: 120 }}
          min={0}
        />
        <input
          type="number"
          placeholder="Max wage ₹"
          value={maxWage}
          onChange={(e) => setMaxWage(e.target.value)}
          style={{ width: 120 }}
          min={0}
        />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="jobs-date-input" title="Filter by job date" />
        {hasFilters && (
          <button className="btn ghost" onClick={clearFilters} data-testid="jobs-clear-filters">✕ Clear filters</button>
        )}
      </div>

      <div className="filter-row">
        {isWorker && (
          <label className="toggle" data-testid="only-available-toggle">
            <input
              type="checkbox"
              checked={availableOnly}
              onChange={(e) => setAvailableOnly(e.target.checked)}
              data-testid="only-available-checkbox"
            />
            <span>Only jobs on my available days</span>
          </label>
        )}
        {showSaved && saved.size === 0 && (
          <span style={{ fontSize: 13, color: "var(--muted)" }}>No saved jobs yet — click ☆ on any job to save it.</span>
        )}
      </div>

      <ErrorBox text={err} />

      {loading ? (
        <div className="grid cols-3">
          {[1, 2, 3, 4, 5, 6].map((n) => <CardSkeleton key={n} />)}
        </div>
      ) : displayJobs.length === 0 ? (
        <Empty
          icon="🔍"
          title={showSaved ? "No saved jobs yet." : availableOnly ? "No jobs on your available days." : "No jobs found."}
          text={showSaved ? "Browse jobs and click the bookmark icon to save them." : availableOnly ? "Open more days on your calendar or turn off the filter." : "Try a different category or check back later."}
        />
      ) : (
        <div className="grid cols-3" data-testid="jobs-list">
          {displayJobs.map((j) => (
            <div className="card job-card" key={j.id} data-testid={`job-card-${j.id}`}>
              <div className="job-card-top">
                <Badge>{j.status}</Badge>
                {token && (
                  <button
                    className="save-btn"
                    onClick={(e) => toggleSave(j.id, e)}
                    title={saved.has(j.id) ? "Remove from saved" : "Save job"}
                    aria-label={saved.has(j.id) ? "Remove from saved" : "Save job"}
                  >
                    {saved.has(j.id) ? "★" : "☆"}
                  </button>
                )}
              </div>
              <h2>{j.title}</h2>
              <p style={{ color: "var(--muted)", fontSize: 13 }}>{j.location}</p>
              <p style={{ fontSize: 13 }}>{j.category} · {j.required_skills || "General"}</p>
              <p className="price">₹{j.wage}</p>
              {j.job_date && <p className="muted" style={{ fontSize: 12 }}>📅 {new Date(j.job_date).toLocaleDateString()}</p>}
              {j.distance_km != null && <p style={{ fontSize: 12, color: "var(--muted)" }}>📍 {j.distance_km} km away</p>}
              <Link className="btn ghost" to={"/jobs/" + j.id} style={{ marginTop: 8 }}>View details</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
