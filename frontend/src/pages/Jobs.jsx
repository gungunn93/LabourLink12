import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { messageOf } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { Badge, Empty, ErrorBox, Loading } from "../components/States";

export default function Jobs() {
  const { user } = useAuth();
  const isWorker = user?.role === "worker";
  const [jobs, setJobs] = useState([]);
  const [cats, setCats] = useState([]);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [date, setDate] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setErr("");
    setLoading(true);
    try {
      const params = { q, category, sort };
      if (date) params.date = date;
      if (availableOnly && isWorker) params.available_only = "true";
      const r = await api.get("/jobs", { params });
      setJobs(r.data.data || []);
    } catch (e) {
      setErr(messageOf(e, "Unable to load jobs"));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    api.get("/categories").then((r) => setCats(r.data.data || [])).catch(() => {});
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [availableOnly, date]);

  const clearFilters = () => {
    setQ(""); setCategory(""); setSort("newest"); setDate(""); setAvailableOnly(false);
    // The useEffect on [availableOnly, date] will re-fetch. If only q/category/sort
    // were dirty, manually trigger a reload using the reset values.
    if (!availableOnly && !date) {
      // no state change on the deps array will fire useEffect, so refetch explicitly
      // with a microtask to ensure state has been applied
      queueMicrotask(() => {
        api.get("/jobs", { params: { q: "", category: "", sort: "newest" } })
          .then((r) => setJobs(r.data.data || []))
          .catch((e) => setErr(messageOf(e, "Unable to load jobs")));
      });
    }
  };

  return (
    <div className="page">
      <p className="crumbs">Home / Jobs</p>
      <h1>Find nearby work</h1>
      <div className="search-row">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, skill or area" data-testid="jobs-search-input" />
        <select value={category} onChange={(e) => setCategory(e.target.value)} data-testid="jobs-category-select">
          <option value="">All categories</option>
          {cats.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} data-testid="jobs-sort-select">
          <option value="newest">Newest</option>
          <option value="wage">Highest wage</option>
          <option value="nearest">Nearest</option>
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} data-testid="jobs-date-input" title="Filter by job date" />
        <button className="btn primary" onClick={load} data-testid="jobs-search-btn">Search</button>
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
        {(q || category || date || availableOnly || sort !== "newest") && (
          <button className="btn ghost" onClick={clearFilters} data-testid="jobs-clear-filters">Clear filters</button>
        )}
      </div>
      <ErrorBox text={err} />
      {loading ? <Loading text="Loading jobs..." /> : jobs.length === 0 ? (
        <Empty
          title={availableOnly ? "No jobs on days you've marked available." : "No jobs available in your area right now."}
          text={availableOnly ? "Open more days on your calendar or turn off the filter." : "Try another category or check back later."}
        />
      ) : (
        <div className="grid cols-3" data-testid="jobs-list">
          {jobs.map((j) => (
            <div className="card" key={j.id} data-testid={`job-card-${j.id}`}>
              <Badge>{j.status}</Badge>
              <h2>{j.title}</h2>
              <p>{j.location}</p>
              <p>{j.category} · {j.required_skills || "General"}</p>
              <p className="price">₹{j.wage}</p>
              {j.job_date && <p className="muted">On {new Date(j.job_date).toLocaleDateString()}</p>}
              {j.distance_km != null && <p>{j.distance_km} km away</p>}
              <Link className="btn ghost" to={"/jobs/" + j.id}>View details</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
