export const money = (value) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value || 0);

export const number = (value) =>
  value === null || value === undefined
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2
      }).format(value);

export const percent = (value) =>
  value === null || value === undefined
    ? "—"
    : `${value > 0 ? "+" : ""}${value}%`;

export const formatEvidence = (item) => {
  if (item.format === "currency") return money(item.value);
  if (item.format === "percent") return percent(item.value);
  if (item.format === "text") return item.value ?? "—";
  return number(item.value);
};

export const formatTimestamp = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};
