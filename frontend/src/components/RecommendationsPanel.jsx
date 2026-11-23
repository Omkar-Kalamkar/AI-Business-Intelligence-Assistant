import { Lightbulb } from "lucide-react";

import { formatEvidence } from "../format";

const PRIORITY_LABELS = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority"
};

export default function RecommendationsPanel({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="chart-card insight-panel">
      <h3>
        <Lightbulb size={18} /> AI Business Recommendations
      </h3>

      <p className="muted-note">
        Generated from verified analysis results. Every recommendation
        includes its reason and supporting figures.
      </p>

      <div className="recommendation-cards">
        {recommendations.map((item) => (
          <div
            key={item.id}
            className={`recommendation-card priority-${item.priority}`}
          >
            <div className="recommendation-header">
              <h4>{item.title}</h4>
              <span className={`priority-badge priority-${item.priority}`}>
                {PRIORITY_LABELS[item.priority] || item.priority}
              </span>
            </div>

            <p>{item.recommendation}</p>

            <p className="recommendation-reason">
              <strong>Why:</strong> {item.reason}
            </p>

            {item.evidence.length > 0 && (
              <div className="evidence-chips">
                {item.evidence.map((evidence) => (
                  <span
                    key={evidence.label}
                    className="evidence-chip"
                  >
                    {evidence.label}:{" "}
                    <strong>{formatEvidence(evidence)}</strong>
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
