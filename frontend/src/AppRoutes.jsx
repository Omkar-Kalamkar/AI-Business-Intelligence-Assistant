import { Navigate, Route, Routes } from "react-router-dom";

import App from "./App";
import ProtectedRoute from "./auth/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<App />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
