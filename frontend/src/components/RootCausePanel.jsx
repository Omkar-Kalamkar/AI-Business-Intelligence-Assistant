import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { GitBranch } from "lucide-react";

import { money, number, percent } from "../format";

export default function RootCausePanel({ rootCause }) {
  const [activeDimension, setActiveDimension] = useState(0);

  if (!rootCause) return null;

  if (!rootCause.available) {
    return (
      <div className="chart-card insight-panel">
        <h3>
          <GitBranch size={18} /> Root Cause Analysis
        </h3>
        <p className="muted-note">{rootCause.message}</p>
      </div>
    );
  }

  const isPeriodMode = rootCause.mode === "period_comparison";
  const dimensions = rootCause.dimensions || [];
  const selected = dimensions[activeDimension] || dimensions[0];
  const contributors = selected?.contributors || [];

  const chartData = contributors.map((item) => ({
    name: item.name,
    value: isPeriodMode ? item.change : item.current
  }));

  return (
    <div className="chart-card insight-panel">
      <h3>
        <GitBranch size={18} /> Root Cause Analysis
      </h3>

      {isPeriodMode ? (
        <div className="period-summary">
          <div>
            <p className="muted-note">
              Previous ({rootCause.previous_period})
            </p>
            <strong>{money(rootCause.previous_total)}</strong>
          </div>

          <div>
            <p className="muted-note">
              Current ({rootCause.current_period})
            </p>
            <strong>{money(rootCause.current_total)}</strong>
          </div>

          <div>
            <p className="muted-note">Change</p>
            <strong
              className={
                rootCause.total_change >= 0
                  ? "change-positive"
                  : "change-negative"
              }
            >
              {money(rootCause.total_change)} (
              {percent(rootCause.total_change_pct)})
            </strong>
          </div>
        </div>
      ) : (
        <p className="muted-note">
          Total sales: {money(rootCause.current_total)}
        </p>
      )}

      {dimensions.length > 0 && (
        <div className="dimension-tabs">
          {dimensions.map((breakdown, index) => (
            <button
              key={breakdown.dimension}
              className={
                index === activeDimension ? "tab active" : "tab"
              }
              onClick={() => setActiveDimension(index)}
            >
              {breakdown.dimension.charAt(0).toUpperCase() +
                breakdown.dimension.slice(1)}
            </button>
          ))}
        </div>
      )}

      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => money(value)} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={
                    isPeriodMode
                      ? entry.value >= 0
                        ? "#10b981"
                        : "#ef4444"
                      : "#6366f1"
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {contributors.length > 0 && (
        <div className="table-wrapper">
          <table className="preview-table">
            <thead>
              <tr>
                <th>{selected.dimension}</th>
                {isPeriodMode ? (
                  <>
                    <th>Previous</th>
                    <th>Current</th>
                    <th>Change</th>
                    <th>Change %</th>
                    <th>Share of change</th>
                  </>
                ) : (
                  <>
                    <th>Sales</th>
                    <th>Share of total</th>
                  </>
                )}
              </tr>
            </thead>

            <tbody>
              {contributors.map((item) => (
                <tr key={item.name}>
                  <td>{item.name}</td>

                  {isPeriodMode ? (
                    <>
                      <td>{money(item.previous)}</td>
                      <td>{money(item.current)}</td>
                      <td
                        className={
                          item.change >= 0
                            ? "change-positive"
                            : "change-negative"
                        }
                      >
                        {money(item.change)}
                      </td>
                      <td>{percent(item.change_pct)}</td>
                      <td>{number(item.contribution_pct)}%</td>
                    </>
                  ) : (
                    <>
                      <td>{money(item.current)}</td>
                      <td>{number(item.contribution_pct)}%</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted-note analysis-summary">{rootCause.summary}</p>
    </div>
  );
}
