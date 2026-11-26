import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import App from "./App";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  downloadReport: vi.fn(),
  generateReport: vi.fn(),
  listReports: vi.fn(),
  getReport: vi.fn(),
  deleteReport: vi.fn(),
  downloadCurrentReport: vi.fn(),
  downloadReportFile: vi.fn(),
}));

vi.mock("./api", () => ({
  api: {
    get: mocks.get,
    post: mocks.post,
    delete: mocks.delete,
  },
  downloadReport: mocks.downloadReport,
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

const uploadResponse = {
  message: "Dataset analyzed successfully!",
  filename: "report.csv",
  original_records: 3,
  cleaned_records: 3,
  dataset_id: "dataset-1",
  uploaded_at: "2026-01-01T00:00:00Z",
  analysis: {
    summary: {
      total_records: 3,
      total_columns: 4,
      total_sales: 3000,
      total_profit: 450,
      total_quantity: 12,
      missing_values: 0,
      duplicate_records: 0,
    },
    product_data: [{ name: "Mobile", sales: 3000 }],
    region_data: [{ name: "North", value: 3000 }],
    insights: ["Total sales are 3,000.00."],
    recommendations: ["Focus on Mobile."],
  },
  preview: [{ Date: "2026-01-01", Sales: 1000 }],
};

const insightsResponse = {
  insight_id: 42,
  filename: "report.csv",
  generated_at: "2026-01-01T00:00:00Z",
  summary: uploadResponse.analysis.summary,
  insights: uploadResponse.analysis.insights,
  anomalies: {
    available: false,
    message: "Not enough rows for anomaly detection.",
  },
  trends: {
    available: false,
    message: "Trend analysis needs a date column.",
  },
  root_cause: {
    available: false,
    message: "Root cause analysis is not available.",
  },
  kpi_alerts: {
    available: true,
    mode: "baseline",
    message: "Baseline checks completed.",
    alerts: [],
  },
  recommendations: [
    {
      id: "monitor",
      title: "Monitor KPIs",
      priority: "low",
      recommendation: "Keep monitoring KPIs.",
      reason: "No issues detected.",
      evidence: [],
    },
  ],
};

const uploadFile = async (fileName = "report.csv") => {
  const input = document.querySelector('input[type="file"]');
  const file = new File(["Date,Sales\n2026-01-01,1000"], fileName, {
    type: "text/csv",
  });
  fireEvent.change(input, { target: { files: [file] } });
};

describe("App end-to-end workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mocks.get.mockImplementation((url) => {
      if (url === "/insights") {
        return Promise.resolve({ data: insightsResponse });
      }
      if (url === "/history") {
        return Promise.resolve({ data: { items: [] } });
      }
      return Promise.resolve({ data: {} });
    });

    mocks.post.mockImplementation((url) => {
      if (url === "/upload") {
        return Promise.resolve({ data: uploadResponse });
      }
      return Promise.resolve({ data: { answer: "Answer" } });
    });

    mocks.downloadReport.mockResolvedValue("report_42.pdf");
    mocks.listReports.mockResolvedValue({ data: { items: [] } });
    mocks.generateReport.mockResolvedValue({
      data: {
        id: 7,
        report: {
          title: "Business Intelligence Report",
          filename: "report.csv",
          generated_at: "2026-01-01T00:00:00Z",
          executive_summary: {
            headline: "Business performance overview",
            paragraphs: ["Dataset: report.csv."],
            metrics: [],
            highlights: [],
          },
          kpi_performance: { message: "Baseline checks completed." },
          charts: [],
          tables: [],
          warnings: [],
        },
      },
    });
  });

  it("shows an empty state before a dataset is uploaded", async () => {
    render(<App />);

    expect(screen.getByText(/Welcome to InsightAI/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/No saved insights yet/i)
    ).toBeInTheDocument();
  });

  it("uploads, previews and generates advanced insights", async () => {
    render(<App />);

    await uploadFile();

    expect(await screen.findByText(/Total Revenue/i)).toBeInTheDocument();
    expect(screen.getAllByText(/report\.csv/).length).toBeGreaterThan(0);
    expect(screen.getByText("Dataset Preview")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
    expect(screen.getByText("Anomaly Detection")).toBeInTheDocument();
    expect(screen.getByText("KPI Alerts")).toBeInTheDocument();
    expect(screen.getByText("Root Cause Analysis")).toBeInTheDocument();
    expect(screen.getByText("Monitor KPIs")).toBeInTheDocument();
    expect(mocks.get).toHaveBeenCalledWith("/insights");
  });

  it("shows upload API errors", async () => {
    mocks.post.mockRejectedValueOnce({
      response: { data: { detail: "Invalid file type." } },
    });

    render(<App />);
    await uploadFile("broken.exe");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid file type."
    );
  });

  it("shows insight errors without losing the uploaded dataset", async () => {
    mocks.get.mockImplementation((url) => {
      if (url === "/insights") {
        return Promise.reject({
          response: { data: { detail: "Insight service unavailable." } },
        });
      }
      return Promise.resolve({ data: { items: [] } });
    });

    render(<App />);
    await uploadFile();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Insight service unavailable."
    );
    expect(screen.getByText(/Total Revenue/i)).toBeInTheDocument();
  });

  it("prevents duplicate upload requests", async () => {
    let resolveUpload;
    mocks.post.mockImplementation(() => new Promise((resolve) => {
      resolveUpload = resolve;
    }));

    render(<App />);
    await uploadFile("first.csv");
    await uploadFile("second.csv");

    await waitFor(() => {
      expect(mocks.post).toHaveBeenCalledTimes(1);
    });

    resolveUpload(uploadResponse);
  });

  it("downloads a PDF report for the generated insight", async () => {
    render(<App />);
    await uploadFile();

    const downloadButton = await screen.findByRole("button", {
      name: /Download PDF Report/i,
    });
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(mocks.downloadReport).toHaveBeenCalledWith(42);
    });
  });

  it("generates a report from the reports section", async () => {
    render(<App />);

    expect(screen.getAllByText(/Reports/i).length).toBeGreaterThan(0);
    expect(
      await screen.findByText(/No saved reports yet/i)
    ).toBeInTheDocument();

    await uploadFile();
    await screen.findByText("Dataset Preview");
    fireEvent.click(
      await screen.findByRole("button", { name: /^Generate Report$/i })
    );

    await waitFor(() => {
      expect(mocks.generateReport).toHaveBeenCalledWith({});
    });
    expect(
      await screen.findByText("Business performance overview")
    ).toBeInTheDocument();
  });
});
