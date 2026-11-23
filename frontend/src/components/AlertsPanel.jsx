import { useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  CheckCircle2
} from "lucide-react";

import SeverityBadge from "./SeverityBadge";
import { money, number, percent } from "../format";

const formatAlertValue = (alert, value) => {
  if (value === null || value === undefined) return "—";
  if (alert.is_margin) return `${number(value)}%`;
  if (alert.kpi === "order_count" || alert.id === "negative_sales_records") {
    return number(value);
  }
  return money(value);
};

export default function AlertsPanel({ alerts }) {
  const [reviewed, setReviewed] = useState(() => new Set());
  const [hideReviewed, setHideReviewed] = useState(false);

  if (!alerts) return null;

  const toggleReviewed = (id) => {
    setReviewed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (!alerts.available) {
    return (
      <div className="chart-card insight-panel" id="kpi-alerts">
        <h3>
          <Bell size={18} /> KPI Alerts
        </h3>
        <p className="muted-note">{alerts.message}</p>
      </div>
    );
  }

  const visible = alerts.alerts.filter(
    (alert) => !hideReviewed || !reviewed.has(alert.id)
  );

  return (
    <div className="chart-card insight-panel" id="kpi-alerts">
      <div className="panel-header">
        <h3>
          <Bell size={18} /> KPI Alerts
          {alerts.alerts.length > 0 && (
            <span className="alert-count">{alerts.alerts.length}</span>
          )}
        </h3>

        {alerts.alerts.length > 0 && (
          <label className="review-filter">
            <input
              type="checkbox"
              checked={hideReviewed}
              onChange={(event) =>
                setHideReviewed(event.target.checked)
              }
            />
            Hide reviewed
          </label>
        )}
      </div>

      <p className="muted-note">
        {alerts.mode === "period_comparison"
          ? `Comparing ${alerts.previous_period} with ${alerts.current_period}.`
          : "Baseline checks (no comparable time periods found)."}
      </p>

      {visible.length === 0 ? (
        <p className="success-note">
          <CheckCircle2 size={16} />
          {alerts.alerts.length === 0
            ? "No significant KPI changes detected."
            : "All alerts reviewed."}
        </p>
      ) : (
        <div className="alerts-list">
          {visible.map((alert) => (
            <div
              key={alert.id}
              className={
                reviewed.has(alert.id)
                  ? `alert-card alert-${alert.severity} reviewed`
                  : `alert-card alert-${alert.severity}`
              }
            >
              <div className="alert-header">
                <span className="alert-direction">
                  {alert.direction === "increase" ? (
                    <ArrowUpRight size={18} />
                  ) : (
                    <ArrowDownRight size={18} />
                  )}
                  {alert.label}
                </span>

                <SeverityBadge severity={alert.severity} />
              </div>

              <p className="alert-message">{alert.message}</p>

              <div className="alert-figures">
                {alert.previous !== null && (
                  <span>
                    Previous:{" "}
                    <strong>
                      {formatAlertValue(alert, alert.previous)}
                    </strong>
                  </span>
                )}
                <span>
                  Current:{" "}
                  <strong>
                    {formatAlertValue(alert, alert.current)}
                  </strong>
                </span>
                {alert.change_pct !== null && (
                  <span>
                    Change:{" "}
                    <strong>{percent(alert.change_pct)}</strong>
                  </span>
                )}
              </div>

              <button
                className="review-button"
                onClick={() => toggleReviewed(alert.id)}
              >
                {reviewed.has(alert.id)
                  ? "Mark as unreviewed"
                  : "Mark as reviewed"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
