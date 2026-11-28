import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./authContext";

export default function ProtectedRoute({ allowedRoles }) {
  const auth = useAuth();
  const location = useLocation();

  if (!auth || auth.loading) {
    return <div className="auth-loading">Checking your session...</div>;
  }

  if (!auth.user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(auth.user.role)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
