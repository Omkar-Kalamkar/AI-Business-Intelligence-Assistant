import { createContext, useContext } from "react";

export const ROLES = {
  ADMIN: "admin",
  ANALYST: "analyst",
  VIEWER: "viewer"
};

export const canWriteRoles = [ROLES.ADMIN, ROLES.ANALYST];

export const canWrite = (user) => canWriteRoles.includes(user?.role);

export const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);
