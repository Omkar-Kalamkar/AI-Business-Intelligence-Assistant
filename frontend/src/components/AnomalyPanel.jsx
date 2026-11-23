import { useState } from "react";
import { Activity } from "lucide-react";

import SeverityBadge from "./SeverityBadge";
import { number } from "../format";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];
const MAX_VISIBLE = 20;

export default function AnomalyPanel({ anomalies }) {
  const [severityFilter, setSeverityFilter] = useState("all");

  if (!anomalies) return null;

  if (!anomalies.available) {
    return (
      <div className="chart-card insight-panel">
        <h3>
          <Activity size={18} /> Anomaly Detection
        </h3>
        <p className="muted-note">{anomalies.message}</p>
      </div>
    );
  }

  const filtered = anomalies.anomalies.filter(
    (item) =>
      severityFilter === "all" || item.severity === severityFilter
  );
  const visible = filtered.slice(0, MAX_VISIBLE);

  return (
    <div className="chart-card insight-panel">
      <div className="panel-header">
        <h3>
          <Activity size={18} /> Anomaly Detection
        </h3>

        <select
          value={severityFilter}
          onChange={(event) => setSeverityFilter(event.target.value)}
          aria-label="Filter anomalies by severity"
        >
          <option value="all">All severities</option>
          {SEVERITY_ORDER.map((severity) => (
            <option key={severity} value={severity}>
              {severity.charAt(0).toUpperCase() + severity.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <p className="muted-note">
        {anomalies.anomaly_count} unusual record(s) out of{" "}
        {anomalies.total_records} rows, using robust z-scores and
        Isolation Forest.
      </p>

      <div className="severity-summary">
        {SEVERITY_ORDER.map((severity) => (
          <span
            key={severity}
            className={`severity-chip severity-${severity}`}
          >
            {severity}: {anomalies.severity_counts[severity] || 0}
          </span>
        ))}
      </div>

      {visible.length > 0 ? (
        <div className="table-wrapper">
          <table className="preview-table anomaly-table">
            <thead>
              <tr>
                <th>Row</th>
                <th>Severity</th>
                <th>Flagged values</th>
                <th>Detected by</th>
              </tr>
            </thead>

            <tbody>
              {visible.map((item) => (
                <tr key={item.row_index}>
                  <td>{item.row_index}</td>

                  <td>
                    <SeverityBadge severity={item.severity} />
                  </td>

                  <td>
                    {item.flagged_columns.length > 0 ? (
                      item.flagged_columns.map((flag) => (
                        <div
                          key={flag.column}
                          className="flagged-value"
                        >
                          <strong>{flag.column}</strong> ={" "}
                          {number(flag.value)}{" "}
                          <span className="muted-note">
                            (typical {number(flag.expected_median)},
                            range {number(flag.lower_bound)} –{" "}
                            {number(flag.upper_bound)}, z ={" "}
                            {flag.zscore})
                          </span>
                        </div>
                      ))
                    ) : (
                      <span className="muted-note">
                        Multivariate outlier (Isolation Forest)
                      </span>
                    )}
                  </td>

                  <td className="muted-note">
                    {item.detected_by.replaceAll("_", " ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length > MAX_VISIBLE && (
            <p className="muted-note">
              Showing {MAX_VISIBLE} of {filtered.length} filtered
              anomalies.
            </p>
          )}
        </div>
      ) : (
        <p className="muted-note">
          No anomalies match the selected severity.
        </p>
      )}
    </div>
  );
}
