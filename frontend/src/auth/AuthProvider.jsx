import {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  changePassword as changePasswordApi,
  clearToken,
  fetchCurrentUser,
  getApiError,
  getToken,
  login as loginApi,
  logout as logoutApi,
  register as registerApi,
  setToken,
  UNAUTHORIZED_EVENT,
  updateProfile as updateProfileApi
} from "../api";
import { AuthContext, canWrite } from "./authContext";

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setAuthToken] = useState(() => getToken());
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [error, setError] = useState("");

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setAuthToken(null);
      setError("");
    };

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  useEffect(() => {
    if (!getToken()) return;

    let active = true;
    fetchCurrentUser()
      .then((response) => {
        if (active) setUser(response.data);
      })
      .catch(() => {
        if (active) {
          clearToken();
          setAuthToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email, password) => {
    setError("");
    try {
      const response = await loginApi(email, password);
      setToken(response.data.access_token);
      setAuthToken(response.data.access_token);
      setUser(response.data.user);
      setLoading(false);
      return response.data;
    } catch (err) {
      const message = getApiError(err, "Unable to sign in.");
      setError(message);
      throw err;
    }
  }, []);

  const registerAccount = useCallback(async (payload) => {
    setError("");
    try {
      const response = await registerApi(payload);
      return response.data;
    } catch (err) {
      const message = getApiError(err, "Unable to create the account.");
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getToken()) await logoutApi();
    } catch {
      return;
    } finally {
      clearToken();
      setAuthToken(null);
      setUser(null);
      setError("");
      setLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (payload) => {
    setError("");
    try {
      const response = await updateProfileApi(payload);
      if (payload.new_password) {
        clearToken();
        setAuthToken(null);
        setUser(null);
      } else {
        setUser(response.data.user);
      }
      return response.data;
    } catch (err) {
      const message = getApiError(err, "Unable to update the profile.");
      setError(message);
      throw err;
    }
  }, []);

  const changePassword = useCallback(async (payload) => {
    setError("");
    try {
      const response = await changePasswordApi(payload);
      clearToken();
      setAuthToken(null);
      setUser(null);
      return response.data;
    } catch (err) {
      const message = getApiError(err, "Unable to change the password.");
      setError(message);
      throw err;
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      error,
      login,
      registerAccount,
      logout,
      updateProfile,
      changePassword,
      canWrite: canWrite(user)
    }),
    [
      user,
      token,
      loading,
      error,
      login,
      registerAccount,
      logout,
      updateProfile,
      changePassword
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
