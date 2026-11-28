import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";

import { useAuth } from "../auth/authContext";

export default function RegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  if (auth && !auth.loading && auth.user) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);

    try {
      await auth.registerAccount({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role
      });
      await auth.login(email.trim(), password);
      navigate("/", { replace: true });
    } catch {
      setFormError("Registration failed. Please review the details and try again.");
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

        <h1>Create your account</h1>
        <p className="muted-note">
          The first account on a new deployment must be an Administrator.
          Later accounts are created as Viewers.
        </p>

        {message && (
          <div className="error-message" role="alert">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="register-name">Full name</label>
          <div className="auth-input">
            <UserRound size={18} />
            <input
              id="register-name"
              type="text"
              required
              maxLength={100}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Your name"
            />
          </div>

          <label htmlFor="register-email">Email</label>
          <div className="auth-input">
            <Mail size={18} />
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
            />
          </div>

          <label htmlFor="register-role">Role</label>
          <select
            id="register-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            className="auth-select"
          >
            <option value="viewer">Viewer</option>
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
          </select>

          <label htmlFor="register-password">Password</label>
          <div className="auth-input">
            <LockKeyhole size={18} />
            <input
              id="register-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
            />
          </div>

          <button
            className="upload-button auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="auth-footer">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
