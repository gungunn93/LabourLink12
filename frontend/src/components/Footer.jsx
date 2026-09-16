import React from "react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer" data-testid="site-footer">
      <div className="footer-brand"><Link to="/" data-testid="footer-brand-link">Labour<span>Link</span></Link><p>Fair work, trusted connections.</p></div>
      <div className="footer-links" data-testid="footer-navigation">
        <Link to="/">Home</Link><Link to="/jobs">Find Jobs</Link><Link to="/employer/jobs/new">Post a Job</Link>
        <Link to="/about">About</Link><Link to="/contact">Contact</Link><Link to="/help">Help &amp; Support</Link>
        <Link to="/privacy">Privacy Policy</Link><Link to="/terms">Terms &amp; Conditions</Link>
      </div>
      <p className="footer-copy" data-testid="footer-copyright">© 2026 LabourLink. All Rights Reserved.</p>
    </footer>
  );
}