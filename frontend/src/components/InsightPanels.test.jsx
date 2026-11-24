import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import AlertsPanel from "./AlertsPanel";
import AnomalyPanel from "./AnomalyPanel";

describe("insight empty states", () => {
  it("shows a success state when there are no KPI alerts", () => {
    render(
      <AlertsPanel
        alerts={{
          available: true,
          mode: "baseline",
          message: "Baseline checks completed.",
          alerts: [],
        }}
      />
    );

    expect(
      screen.getByText(/No significant KPI changes detected/i)
    ).toBeInTheDocument();
  });

  it("shows a message when anomaly detection is unavailable", () => {
    render(
      <AnomalyPanel
        anomalies={{
          available: false,
          message: "Anomaly detection needs at least 8 rows.",
        }}
      />
    );

    expect(
      screen.getByText(/Anomaly detection needs at least 8 rows/i)
    ).toBeInTheDocument();
  });
});
