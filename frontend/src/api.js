import axios from "axios";

export const API_URL = import.meta.env?.VITE_API_URL || "http://127.0.0.1:8000";
export const TOKEN_KEY = "insightai_token";
export const UNAUTHORIZED_EVENT = "insightai:unauthorized";

export const api = axios.create({
  baseURL: API_URL
});

const storage = () => {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
};

export const getToken = () => storage()?.getItem(TOKEN_KEY) || null;

export const setToken = (token) => {
  try {
    storage()?.setItem(TOKEN_KEY, token);
  } catch {
    return;
  }
};

export const clearToken = () => {
  try {
    storage()?.removeItem(TOKEN_KEY);
  } catch {
    return;
  }
};

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401 && getToken()) {
      clearToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
      }
    }
    return Promise.reject(error);
  }
);

export const getApiError = (error, fallback) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
};

export const downloadReport = async (insightId) => {
  const path = insightId ? `/report/${insightId}` : "/report";
  const response = await api.get(path, { responseType: "blob" });

  const disposition = response.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match
    ? match[1]
    : insightId
      ? `insight-${insightId}.pdf`
      : "business-insights.pdf";

  const objectUrl = URL.createObjectURL(
    new Blob([response.data], { type: "application/pdf" })
  );
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);

  return filename;
};

const extensionFor = (format) => (format === "excel" ? "xlsx" : "pdf");

const mediaTypeFor = (format) => (
  format === "excel"
    ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    : "application/pdf"
);

const saveBlobResponse = async (request, fallbackFilename, format) => {
  const response = await request;
  const disposition = response.headers?.["content-disposition"] || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match ? match[1] : fallbackFilename;

  const objectUrl = URL.createObjectURL(
    new Blob([response.data], { type: mediaTypeFor(format) })
  );
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);

  return filename;
};

export const generateReport = (payload = {}) => api.post("/reports", payload);

export const listReports = () => api.get("/reports");

export const getReport = (reportId) => api.get(`/reports/${reportId}`);

export const deleteReport = (reportId) => api.delete(`/reports/${reportId}`);

export const downloadCurrentReport = (format) =>
  saveBlobResponse(
    api.get(`/reports/current/${format}`, { responseType: "blob" }),
    `business-report.${extensionFor(format)}`,
    format
  );

export const downloadReportFile = (reportId, format) =>
  saveBlobResponse(
    api.get(`/reports/${reportId}/${format}`, { responseType: "blob" }),
    `report-${reportId}.${extensionFor(format)}`,
    format
  );

export const login = (email, password) =>
  api.post("/auth/login", { email, password });

export const register = (payload) => api.post("/auth/register", payload);

export const fetchCurrentUser = () => api.get("/auth/me");

export const updateProfile = (payload) => api.patch("/auth/profile", payload);

export const changePassword = (payload) =>
  api.post("/auth/change-password", payload);

export const logout = () => api.post("/auth/logout");
