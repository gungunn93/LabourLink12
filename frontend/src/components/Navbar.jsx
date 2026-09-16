import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
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
            <NavLink to="/messages">Chat</NavLink>
            <NavLink to="/payments">Earnings</NavLink>
            <NavLink to="/notifications">Alerts</NavLink>
            <NavLink to="/profile">Profile</NavLink>
          </>
        )}
        {token && user?.role === "employer" && (
          <>
            <NavLink to="/employer/dashboard">Dashboard</NavLink>
            <NavLink to="/employer/jobs/new">Post job</NavLink>
            <NavLink to="/applications">Applications</NavLink>
            <NavLink to="/negotiation">Negotiate</NavLink>
            <NavLink to="/messages">Chat</NavLink>
            <NavLink to="/payments">Payments</NavLink>
            <NavLink to="/notifications">Alerts</NavLink>
            <NavLink to="/profile">Profile</NavLink>
          </>
        )}
        {token && user?.role === "admin" && (
          <>
            <NavLink to="/admin/dashboard">Admin</NavLink>
            <NavLink to="/notifications">Alerts</NavLink>
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
