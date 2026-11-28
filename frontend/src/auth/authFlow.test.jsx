import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthProvider from "./AuthProvider";
import ProtectedRoute from "./ProtectedRoute";
import LoginPage from "../pages/LoginPage";
import ProfilePage from "../pages/ProfilePage";
import RegisterPage from "../pages/RegisterPage";
import {
  changePassword,
  clearToken,
  fetchCurrentUser,
  getToken,
  login,
  logout,
  register,
  setToken,
  updateProfile
} from "../api";

vi.mock("../api", () => ({
  changePassword: vi.fn(),
  clearToken: vi.fn(),
  fetchCurrentUser: vi.fn(),
  getApiError: vi.fn((error, fallback) => (
    error?.response?.data?.detail || fallback
  )),
  getToken: vi.fn(() => null),
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  setToken: vi.fn(),
  updateProfile: vi.fn(),
  UNAUTHORIZED_EVENT: "insightai:unauthorized"
}));

const user = {
  id: 1,
  email: "admin@example.com",
  full_name: "Admin User",
  role: "admin",
  is_active: true,
  created_at: "2026-01-01T00:00:00+00:00"
};

const renderRoutes = (initialPath = "/login") =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<div>Dashboard content</div>} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );

describe("authentication flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getToken.mockReturnValue(null);
    fetchCurrentUser.mockResolvedValue({ data: user });
    login.mockResolvedValue({
      data: { access_token: "test-token", user }
    });
    register.mockResolvedValue({ data: { message: "created", user } });
    logout.mockResolvedValue({ data: { message: "logged out" } });
    updateProfile.mockResolvedValue({
      data: { message: "Profile updated successfully.", user }
    });
    changePassword.mockResolvedValue({ data: { message: "changed" } });
  });

  it("redirects unauthenticated users from protected routes", async () => {
    renderRoutes("/");

    expect(await screen.findByRole("button", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.queryByText("Dashboard content")).not.toBeInTheDocument();
  });

  it("signs in and navigates to the protected dashboard", async () => {
    const ui = userEvent.setup();
    renderRoutes("/login");

    await ui.type(screen.getByLabelText("Email"), "admin@example.com");
    await ui.type(screen.getByLabelText("Password"), "StrongPass123!");
    await ui.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Dashboard content")).toBeInTheDocument();
    });
    expect(setToken).toHaveBeenCalledWith("test-token");
  });

  it("shows the server error for invalid credentials", async () => {
    const ui = userEvent.setup();
    login.mockRejectedValue({
      response: { data: { detail: "Incorrect email or password." } }
    });
    renderRoutes("/login");

    await ui.type(screen.getByLabelText("Email"), "admin@example.com");
    await ui.type(screen.getByLabelText("Password"), "WrongPass123!");
    await ui.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByRole("alert")
    ).toHaveTextContent("Incorrect email or password.");
  });

  it("registers an account and signs the new user in", async () => {
    const ui = userEvent.setup();
    renderRoutes("/register");

    await ui.type(screen.getByLabelText("Full name"), "New Admin");
    await ui.type(screen.getByLabelText("Email"), "new@example.com");
    await ui.type(screen.getByLabelText("Password"), "StrongPass123!");
    await ui.selectOptions(screen.getByLabelText("Role"), "admin");
    await ui.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText("Dashboard content")).toBeInTheDocument();
    });
    expect(register).toHaveBeenCalledWith({
      full_name: "New Admin",
      email: "new@example.com",
      password: "StrongPass123!",
      role: "admin"
    });
    expect(login).toHaveBeenCalledWith("new@example.com", "StrongPass123!");
  });

  it("loads the profile for a stored token and saves updates", async () => {
    const ui = userEvent.setup();
    getToken.mockReturnValue("stored-token");
    renderRoutes("/profile");

    expect(await screen.findByText("admin@example.com")).toBeInTheDocument();
    await ui.clear(screen.getByLabelText("Full name"));
    await ui.type(screen.getByLabelText("Full name"), "Updated Admin");
    await ui.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({
        full_name: "Updated Admin",
        email: "admin@example.com"
      });
    });
  });

  it("logs out and clears the stored token", async () => {
    const ui = userEvent.setup();
    getToken.mockReturnValue("stored-token");
    renderRoutes("/profile");

    await screen.findByText("admin@example.com");
    await ui.click(screen.getByRole("button", { name: /log out/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });
    expect(clearToken).toHaveBeenCalled();
    expect(logout).toHaveBeenCalled();
  });
});
