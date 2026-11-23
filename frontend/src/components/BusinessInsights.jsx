import { RefreshCw } from "lucide-react";

import AlertsPanel from "./AlertsPanel";
import AnomalyPanel from "./AnomalyPanel";
import TrendChart from "./TrendChart";
import RootCausePanel from "./RootCausePanel";
import RecommendationsPanel from "./RecommendationsPanel";
import { formatTimestamp } from "../format";

export default function BusinessInsights({
  insights,
  onRefresh,
  refreshing = false,
  showRefresh = true
}) {
  if (!insights) return null;

  return (
    <section className="business-insights" id="business-insights">
      <div className="section-header">
        <h2>Business Insights</h2>

        <div className="section-header-actions">
          {insights.generated_at && (
            <span className="muted-note">
              Generated {formatTimestamp(insights.generated_at)}
            </span>
          )}

          {showRefresh && onRefresh && (
            <button
              className="upload-button secondary-button"
              onClick={onRefresh}
              disabled={refreshing}
            >
              <RefreshCw size={16} />
              {refreshing ? "Refreshing..." : "Refresh Insights"}
            </button>
          )}
        </div>
      </div>

      <AlertsPanel alerts={insights.kpi_alerts} />

      <div className="insights-grid">
        <AnomalyPanel anomalies={insights.anomalies} />
        <TrendChart trends={insights.trends} />
      </div>

      <RootCausePanel rootCause={insights.root_cause} />

      <RecommendationsPanel
        recommendations={insights.recommendations}
      />
    </section>
  );
}
