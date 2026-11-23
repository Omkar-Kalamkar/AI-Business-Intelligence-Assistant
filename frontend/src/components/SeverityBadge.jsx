const SEVERITY_LABELS = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  warning: "Warning"
};

export default function SeverityBadge({ severity }) {
  if (!severity) return null;

  return (
    <span className={`severity-badge severity-${severity}`}>
      {SEVERITY_LABELS[severity] || severity}
    </span>
  );
}
