import React, { useEffect, useState, useCallback } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSocket } from "../context/SocketContext";
import api from "../services/api";

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const socket = useSocket();
  const navigate = useNavigate();
  const [counts, setCounts] = useState({ notifications: 0, messages: 0 });

  const fetchCounts = useCallback(() => {
    if (!token) { setCounts({ notifications: 0, messages: 0 }); return; }
    api.get("/notifications/unread-count")
      .then((r) => setCounts(r.data.data || { notifications: 0, messages: 0 }))
      .catch(() => {});
  }, [token]);

  // Fetch on mount and whenever token changes
  useEffect(() => { fetchCounts(); }, [fetchCounts]);

  // Refresh counts when a new notification or message arrives via socket
  useEffect(() => {
    if (!socket) return;
    socket.on("notification:new", fetchCounts);
    socket.on("chat:message", fetchCounts);
    return () => {
      socket.off("notification:new", fetchCounts);
      socket.off("chat:message", fetchCounts);
    };
  }, [socket, fetchCounts]);

  const out = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="topnav">
      <Link className="brand" to="/">Labour<span>Link</span></Link>
      <div className="nav-links">
        {!token && (
          <>
            <NavLink to="/jobs">Browse jobs</NavLink>
            <NavLink to="/login">Login</NavLink>
            <NavLink to="/register">Register</NavLink>
          </>
        )}
        {token && user?.role === "worker" && (
          <>
            <NavLink to="/worker/dashboard">Dashboard</NavLink>
            <NavLink to="/jobs">Jobs</NavLink>
            <NavLink to="/applications">Applications</NavLink>
            <NavLink to="/negotiation">Negotiate</NavLink>
            <NavLink to="/messages" className={({ isActive }) => isActive ? "active" : ""}>
              Chat {counts.messages > 0 && <span className="nav-badge">{counts.messages > 9 ? "9+" : counts.messages}</span>}
            </NavLink>
            <NavLink to="/payments">Earnings</NavLink>
            <NavLink to="/notifications" className={({ isActive }) => isActive ? "active" : ""}>
              Alerts {counts.notifications > 0 && <span className="nav-badge">{counts.notifications > 9 ? "9+" : counts.notifications}</span>}
            </NavLink>
            <NavLink to="/profile">Profile</NavLink>
          </>
        )}
        {token && user?.role === "employer" && (
          <>
            <NavLink to="/employer/dashboard">Dashboard</NavLink>
            <NavLink to="/employer/jobs/new">Post job</NavLink>
            <NavLink to="/applications">Applications</NavLink>
            <NavLink to="/negotiation">Negotiate</NavLink>
            <NavLink to="/messages" className={({ isActive }) => isActive ? "active" : ""}>
              Chat {counts.messages > 0 && <span className="nav-badge">{counts.messages > 9 ? "9+" : counts.messages}</span>}
            </NavLink>
            <NavLink to="/payments">Payments</NavLink>
            <NavLink to="/notifications" className={({ isActive }) => isActive ? "active" : ""}>
              Alerts {counts.notifications > 0 && <span className="nav-badge">{counts.notifications > 9 ? "9+" : counts.notifications}</span>}
            </NavLink>
            <NavLink to="/profile">Profile</NavLink>
          </>
        )}
        {token && user?.role === "admin" && (
          <>
            <NavLink to="/admin/dashboard">Admin</NavLink>
            <NavLink to="/notifications" className={({ isActive }) => isActive ? "active" : ""}>
              Alerts {counts.notifications > 0 && <span className="nav-badge">{counts.notifications > 9 ? "9+" : counts.notifications}</span>}
            </NavLink>
          </>
        )}
      </div>
      {token && user && (
        <div className="user-chip">
          <div className="avatar">{user.name?.[0]?.toUpperCase()}</div>
          <button className="btn ghost" onClick={out}>Logout</button>
        </div>
      )}
    </nav>
  );
}
