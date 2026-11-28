import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { LockKeyhole, Mail, ShieldCheck } from "lucide-react";

import { useAuth } from "../auth/authContext";

export default function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  if (auth && !auth.loading && auth.user) {
    return <Navigate to={location.state?.from?.pathname || "/"} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);

    try {
      await auth.login(email.trim(), password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch {
      setFormError("Sign in failed. Check your credentials and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const message = auth?.error || formError || "";

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <ShieldCheck size={28} />
          <span>InsightAI</span>
        </div>

        <h1>Welcome back</h1>
        <p className="muted-note">
          Sign in to access your private dashboards, datasets and reports.
        </p>

        {message && (
          <div className="error-message" role="alert">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="login-email">Email</label>
          <div className="auth-input">
            <Mail size={18} />
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
            />
          </div>

          <label htmlFor="login-password">Password</label>
          <div className="auth-input">
            <LockKeyhole size={18} />
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
            />
          </div>

          <button
            className="upload-button auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="auth-footer">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
