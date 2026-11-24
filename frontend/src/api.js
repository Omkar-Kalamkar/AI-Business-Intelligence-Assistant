import axios from "axios";

export const API_URL = "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_URL
});

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
