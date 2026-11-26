import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ReportsPanel from "./ReportsPanel";

const mocks = vi.hoisted(() => ({
  generateReport: vi.fn(),
  listReports: vi.fn(),
  getReport: vi.fn(),
  deleteReport: vi.fn(),
  downloadCurrentReport: vi.fn(),
  downloadReportFile: vi.fn(),
}));

vi.mock("../api", () => ({
  generateReport: mocks.generateReport,
  listReports: mocks.listReports,
  getReport: mocks.getReport,
  deleteReport: mocks.deleteReport,
  downloadCurrentReport: mocks.downloadCurrentReport,
  downloadReportFile: mocks.downloadReportFile,
  getApiError: (error, fallback) =>
    error?.response?.data?.detail || fallback,
}));

vi.mock("recharts", () => {
  const passthrough = ({ children }) => children;
  return {
    Bar: passthrough,
    BarChart: passthrough,
    CartesianGrid: passthrough,
    Cell: passthrough,
    Line: passthrough,
    LineChart: passthrough,
    Pie: passthrough,
    PieChart: passthrough,
    ReferenceLine: passthrough,
    ResponsiveContainer: passthrough,
    Tooltip: passthrough,
    XAxis: passthrough,
    YAxis: passthrough,
  };
});

const report = {
  title: "Quarterly Report",
  filename: "sales.csv",
  generated_at: "2026-01-01T00:00:00Z",
  notes: "Board review",
  warnings: ["Sales by Region could not be charted."],
  executive_summary: {
    headline: "Sales grew 12.50% between periods",
    paragraphs: ["Dataset: sales.csv."],
    metrics: [
      { key: "total_sales", label: "Total sales", value: 120000,
        format: "currency" },
    ],
    highlights: ["Top product: Mobile."],
  },
  kpi_performance: {
    message: "2 significant KPI change(s).",
    current_period: "2026-01",
    previous_period: "2025-12",
  },
  charts: [
    {
      id: "product_sales",
      title: "Sales by Product",
      type: "bar",
      format: "currency",
      data: [{ label: "Mobile", value: 120000 }],
    },
    {
      id: "region_sales",
      title: "Sales by Region",
      type: "pie",
      format: "currency",
      data: [{ label: "North", value: 120000 }],
    },
    {
      id: "sales_trend",
      title: "Sales Trend",
      type: "line",
      format: "currency",
      reference: 1000,
      data: [{ label: "Jan", value: 120000, is_anomaly: true }],
    },
  ],
  tables: [
    {
      id: "kpi_performance",
      title: "KPI Performance",
      columns: [
        { key: "label", label: "KPI", format: "text" },
        { key: "current", label: "Current", format: "currency" },
        { key: "change_pct", label: "Change %", format: "percent" },
        { key: "status", label: "Status", format: "text" },
      ],
      rows: [{
        label: "Total Sales",
        current: 120000,
        change_pct: 13.21,
        status: "stable",
      }],
      message: "",
    },
    {
      id: "recommendations",
      title: "Business Recommendations",
      columns: [
        { key: "title", label: "Title", format: "text" },
        { key: "recommendation", label: "Action", format: "text" },
      ],
      rows: [{
        title: "Investigate anomalies",
        recommendation: "Review flagged records.",
      }],
      message: "",
    },
    {
      id: "anomalies",
      title: "Anomaly Detection",
      columns: [],
      rows: [],
      message: "No anomalies were detected.",
    },
  ],
};

const historyItem = {
  id: 12,
  created_at: "2026-01-01T00:00:00Z",
  filename: "sales.csv",
  kind: "business_report",
  record_count: 100,
};

describe("ReportsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listReports.mockResolvedValue({ data: { items: [] } });
    mocks.generateReport.mockResolvedValue({
      data: { id: 7, report },
    });
    mocks.getReport.mockResolvedValue({
      data: { id: 12, payload: report },
    });
    mocks.deleteReport.mockResolvedValue({ data: { deleted: true, id: 12 } });
    mocks.downloadCurrentReport.mockResolvedValue("sales.pdf");
    mocks.downloadReportFile.mockResolvedValue("sales_12.xlsx");
  });

  it("shows an empty state before a dataset is uploaded", async () => {
    render(<ReportsPanel />);

    expect(
      screen.getByText(/Upload a dataset to generate a report/i)
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/No saved reports yet/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate Report/i })).toBeDisabled();
  });

  it("generates and previews a report with charts and tables", async () => {
    render(<ReportsPanel dataset={{ filename: "sales.csv" }} datasetId="d1" />);

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));

    await waitFor(() => {
      expect(mocks.generateReport).toHaveBeenCalledWith({});
    });

    expect(
      await screen.findByText("Sales grew 12.50% between periods")
    ).toBeInTheDocument();
    expect(screen.getByText("Sales by Product")).toBeInTheDocument();
    expect(screen.getByText("Sales by Region")).toBeInTheDocument();
    expect(screen.getByText("Sales Trend")).toBeInTheDocument();
    expect(screen.getByText("Total sales")).toBeInTheDocument();
    expect(screen.getByText("Review flagged records.")).toBeInTheDocument();
    expect(screen.getByText("No anomalies were detected.")).toBeInTheDocument();
    expect(screen.getByText(/Sales by Region could not be charted/i))
      .toBeInTheDocument();
  });

  it("downloads current and saved reports in both formats", async () => {
    mocks.listReports.mockResolvedValue({ data: { items: [historyItem] } });
    render(<ReportsPanel dataset={{ filename: "sales.csv" }} datasetId="d1" />);

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));
    await screen.findByText("Sales grew 12.50% between periods");

    fireEvent.click(
      screen.getAllByRole("button", { name: /Download PDF/i })[0]
    );
    await waitFor(() => {
      expect(mocks.downloadCurrentReport).toHaveBeenCalledWith("pdf");
    });

    fireEvent.click(
      screen.getAllByRole("button", { name: /Download Excel/i })[0]
    );
    await waitFor(() => {
      expect(mocks.downloadCurrentReport).toHaveBeenCalledWith("excel");
    });

    fireEvent.click(screen.getByTitle("Download PDF"));
    await waitFor(() => {
      expect(mocks.downloadReportFile).toHaveBeenCalledWith(12, "pdf");
    });

    fireEvent.click(screen.getByTitle("Download Excel"));
    await waitFor(() => {
      expect(mocks.downloadReportFile).toHaveBeenCalledWith(12, "excel");
    });
  });

  it("views and deletes saved reports", async () => {
    mocks.listReports.mockResolvedValue({ data: { items: [historyItem] } });
    render(<ReportsPanel />);

    expect(await screen.findByText("Report")).toBeInTheDocument();

    fireEvent.click(screen.getByTitle("View report"));
    await waitFor(() => {
      expect(mocks.getReport).toHaveBeenCalledWith(12);
    });
    expect(
      await screen.findByText("Sales grew 12.50% between periods")
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTitle("Delete report"));
    await waitFor(() => {
      expect(mocks.deleteReport).toHaveBeenCalledWith(12);
      expect(mocks.listReports).toHaveBeenCalledTimes(2);
    });
  });

  it("shows empty chart messages when a report has no data", async () => {
    mocks.generateReport.mockResolvedValue({
      data: {
        id: 8,
        report: {
          ...report,
          warnings: [],
          charts: [{
            id: "empty",
            title: "Sales by Product",
            type: "bar",
            data: [],
            message: "Product sales data is not available.",
          }],
        },
      },
    });
    render(<ReportsPanel dataset={{ filename: "sales.csv" }} datasetId="d1" />);

    fireEvent.click(screen.getByRole("button", { name: /Generate Report/i }));

    expect(
      await screen.findByText("Product sales data is not available.")
    ).toBeInTheDocument();
  });
});
