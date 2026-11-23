import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { TrendingUp } from "lucide-react";

import { money } from "../format";

const renderDot = (props) => {
  const { cx, cy, payload } = props;

  if (cx === undefined || cy === undefined) return null;

  if (payload.is_anomaly) {
    return (
      <circle
        key={payload.period}
        cx={cx}
        cy={cy}
        r={6}
        fill="#dc2626"
        stroke="#ffffff"
        strokeWidth={2}
      />
    );
  }

  return (
    <circle
      key={payload.period}
      cx={cx}
      cy={cy}
      r={3}
      fill="#6366f1"
    />
  );
};

export default function TrendChart({ trends }) {
  if (!trends) return null;

  if (!trends.available) {
    return (
      <div className="chart-card insight-panel">
        <h3>
          <TrendingUp size={18} /> Sales Trend Anomalies
        </h3>
        <p className="muted-note">{trends.message}</p>
      </div>
    );
  }

  return (
    <div className="chart-card insight-panel">
      <h3>
        <TrendingUp size={18} /> Sales Trend Anomalies
      </h3>

      <p className="muted-note">
        {trends.anomaly_count} unusual period(s) across{" "}
        {trends.period_count} periods. Red points deviate strongly
        from the typical period sales.
      </p>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={trends.periods}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" minTickGap={24} />
          <YAxis />

          <Tooltip
            formatter={(value, name) =>
              name === "sales" ? money(value) : value
            }
            labelFormatter={(label) => `Period: ${label}`}
          />

          <ReferenceLine
            y={trends.expected_median_sales}
            stroke="#94a3b8"
            strokeDasharray="6 4"
            label={{
              value: "typical",
              position: "insideTopRight",
              fill: "#64748b",
              fontSize: 12
            }}
          />

          <Line
            type="monotone"
            dataKey="sales"
            stroke="#6366f1"
            strokeWidth={2}
            dot={renderDot}
            activeDot={{ r: 7 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
