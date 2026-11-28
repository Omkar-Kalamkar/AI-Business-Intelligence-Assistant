import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";

import { useAuth } from "../auth/authContext";

export default function ProfilePage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState(auth?.user?.full_name || "");
  const [email, setEmail] = useState(auth?.user?.email || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setSuccess("");
    setSubmitting(true);

    const payload = {
      full_name: fullName.trim(),
      email: email.trim()
    };
    if (newPassword) {
      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }

    try {
      const result = await auth.updateProfile(payload);
      if (newPassword) {
        navigate("/login", { replace: true });
        return;
      }
      setSuccess(result.message || "Profile updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
    } catch {
      setFormError("Unable to update your profile. Please check the details.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await auth.logout();
    navigate("/login", { replace: true });
  };

  const message = auth?.error || formError || "";

  return (
    <div className="auth-page">
      <div className="auth-card profile-card">
        <div className="auth-brand">
          <ShieldCheck size={28} />
          <span>InsightAI</span>
        </div>

        <h1>Your profile</h1>
        <p className="muted-note">
          Manage your account details and password.
        </p>

        <div className="profile-summary">
          <span className="role-badge">{auth?.user?.role}</span>
          <span>{auth?.user?.email}</span>
          {auth?.user?.created_at && (
            <span className="muted-note">
              Member since {new Date(auth.user.created_at).toLocaleDateString()}
            </span>
          )}
        </div>

        {message && (
          <div className="error-message" role="alert">
            {message}
          </div>
        )}
        {success && <div className="success-note">{success}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="profile-name">Full name</label>
          <div className="auth-input">
            <UserRound size={18} />
            <input
              id="profile-name"
              type="text"
              required
              maxLength={100}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </div>

          <label htmlFor="profile-email">Email</label>
          <div className="auth-input">
            <Mail size={18} />
            <input
              id="profile-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <fieldset className="auth-fieldset">
            <legend>Change password (optional)</legend>

            <label htmlFor="profile-current-password">Current password</label>
            <div className="auth-input">
              <LockKeyhole size={18} />
              <input
                id="profile-current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
            </div>

            <label htmlFor="profile-new-password">New password</label>
            <div className="auth-input">
              <LockKeyhole size={18} />
              <input
                id="profile-new-password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </div>
          </fieldset>

          <button
            className="upload-button auth-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Saving..." : "Save changes"}
          </button>
        </form>

        <div className="profile-actions">
          <button className="secondary-button" onClick={handleLogout}>
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </div>
    </div>
  );
}
