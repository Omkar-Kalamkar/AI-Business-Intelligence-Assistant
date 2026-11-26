import { useCallback, useEffect, useRef, useState } from "react";

import {
  Download,
  Eye,
  FileBarChart,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  Trash2
} from "lucide-react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import {
  deleteReport,
  downloadCurrentReport,
  downloadReportFile,
  generateReport,
  getApiError,
  getReport,
  listReports
} from "../api";
import { formatTimestamp, money, number, percent } from "../format";

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981", "#ec4899"];

const formatValue = (value, format) => {
  if (value === null || value === undefined || value === "") return "—";

  if (format === "currency") return money(value);
  if (format === "percent") return percent(value);
  if (format === "number" || typeof value === "number") return number(value);
  return String(value);
};

const formatCell = (column, row) => {
  const value = row?.[column.key];
  const format = column.format === "auto" ? row?.format : column.format;
  return formatValue(value, format);
};

function ReportTable({ table }) {
  if (!table.rows?.length) {
    return (
      <p className="muted-note">
        {table.message || "No rows were available."}
      </p>
    );
  }

  return (
    <div className="table-wrapper report-table-wrapper">
      <table className="preview-table report-data-table">
        <thead>
          <tr>
            {table.columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {table.columns.map((column) => (
                <td key={column.key}>{formatCell(column, row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportChart({ chart }) {
  const data = chart.data || [];
  const chartFormat = chart.format;
  const tooltipFormatter = (value) => formatValue(value, chartFormat);

  if (!data.length) {
    return (
      <p className="muted-note">
        {chart.message || "No chart data available."}
      </p>
    );
  }

  if (chart.type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            outerRadius={90}
            label
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.label}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip formatter={tooltipFormatter} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chart.type === "line") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" minTickGap={24} />
          <YAxis />
          <Tooltip formatter={tooltipFormatter} />
          {chart.reference !== null && chart.reference !== undefined && (
            <ReferenceLine y={chart.reference} stroke="#94a3b8" />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="label" />
        <YAxis />
        <Tooltip formatter={tooltipFormatter} />
        <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ReportPreview({ report, onDownload, downloading }) {
  const summary = report.executive_summary || {};
  const performance = report.kpi_performance || {};

  return (
    <div className="report-preview">
      <div className="report-preview-header">
        <div>
          <h4>{report.title || "Business Intelligence Report"}</h4>
          <p className="muted-note">
            {report.filename} · Generated{" "}
            {formatTimestamp(report.generated_at)}
          </p>
          {report.notes && <p className="muted-note">{report.notes}</p>}
        </div>

        <div className="report-download-actions">
          <button
            className="upload-button secondary-button"
            onClick={() => onDownload("pdf")}
            disabled={downloading}
          >
            <FileText size={16} />
            {downloading === "pdf" ? "Preparing..." : "Download PDF"}
          </button>

          <button
            className="upload-button secondary-button"
            onClick={() => onDownload("excel")}
            disabled={downloading}
          >
            <FileSpreadsheet size={16} />
            {downloading === "excel" ? "Preparing..." : "Download Excel"}
          </button>
        </div>
      </div>

      {(report.warnings || []).map((warning, index) => (
        <p className="report-warning" key={index}>
          {warning}
        </p>
      ))}

      <div className="report-metrics">
        {(summary.metrics || []).map((metric) => (
          <div className="report-metric" key={metric.key}>
            <span>{metric.label}</span>
            <strong>{formatValue(metric.value, metric.format)}</strong>
          </div>
        ))}
      </div>

      <div className="report-block">
        <h4>Executive Summary</h4>
        <p className="report-headline">{summary.headline}</p>
        {(summary.paragraphs || []).map((paragraph, index) => (
          <p className="muted-note" key={index}>
            {paragraph}
          </p>
        ))}
        <ul className="report-highlights">
          {(summary.highlights || []).map((highlight, index) => (
            <li key={index}>{highlight}</li>
          ))}
        </ul>
      </div>

      <div className="report-block">
        <h4>KPI Performance</h4>
        <p className="muted-note">
          {performance.message || "KPI data was not available."}
        </p>
        {performance.current_period && (
          <p className="muted-note">
            Current period: {performance.current_period}
            {performance.previous_period
              ? ` · Previous period: ${performance.previous_period}`
              : ""}
          </p>
        )}
      </div>

      <div className="report-block">
        <h4>Charts</h4>
        <div className="report-charts-grid">
          {(report.charts || []).map((chart) => (
            <div className="report-chart-card" key={chart.id}>
              <h5>{chart.title}</h5>
              <ReportChart chart={chart} />
            </div>
          ))}
        </div>
      </div>

      <div className="report-block">
        <h4>Data Tables</h4>
        {(report.tables || []).map((table) => (
          <div className="report-table-block" key={table.id}>
            <h5>{table.title}</h5>
            <ReportTable table={table} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ReportsPanel({ dataset }) {
  const [report, setReport] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const generateRequest = useRef(false);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);

    try {
      const response = await listReports();
      setHistory(response.data.items || []);
    } catch (err) {
      setError(getApiError(err, "Unable to load report history."));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    listReports()
      .then((response) => {
        if (active) {
          setHistory(response.data.items || []);
          setHistoryLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(getApiError(err, "Unable to load report history."));
          setHistoryLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const handleGenerate = async () => {
    if (!dataset || generateRequest.current) return;

    generateRequest.current = true;
    setGenerating(true);
    setError("");

    try {
      const response = await generateReport({});
      setReport(response.data.report);
      setSelectedId(response.data.id);
      await loadHistory();
    } catch (err) {
      setError(getApiError(err, "Unable to generate the report."));
    } finally {
      generateRequest.current = false;
      setGenerating(false);
    }
  };

  const handleView = async (id) => {
    if (busyId !== null) return;

    setBusyId(id);
    setError("");

    try {
      const response = await getReport(id);
      setReport(response.data.payload);
      setSelectedId(id);
    } catch (err) {
      setError(getApiError(err, "Unable to load this report."));
    } finally {
      setBusyId(null);
    }
  };

  const handleDownload = async (format, id) => {
    if (downloading) return;

    setDownloading(`${format}-${id || "current"}`);
    setError("");

    try {
      if (id) {
        await downloadReportFile(id, format);
      } else {
        await downloadCurrentReport(format);
      }
    } catch (err) {
      setError(getApiError(err, `Unable to download the ${format} report.`));
    } finally {
      setDownloading("");
    }
  };

  const handleDelete = async (id) => {
    if (busyId !== null) return;

    setBusyId(id);
    setError("");

    try {
      await deleteReport(id);
      if (selectedId === id) {
        setReport(null);
        setSelectedId(null);
      }
      await loadHistory();
    } catch (err) {
      setError(getApiError(err, "Unable to delete this report."));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="chart-card reports-panel" id="reports">
      <div className="panel-header">
        <h3>
          <FileBarChart size={18} /> Reports
        </h3>

        <button
          className="upload-button secondary-button"
          onClick={loadHistory}
          disabled={historyLoading}
        >
          <RefreshCw size={16} />
          {historyLoading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <p className="muted-note">
        Generate a professional report from the current analysis, including
        KPI performance, anomalies, root cause findings and recommendations.
      </p>

      {error && <p className="error-message" role="alert">{error}</p>}

      {!dataset && (
        <p className="muted-note">
          Upload a dataset to generate a report.
        </p>
      )}

      <div className="report-actions">
        <button
          className="upload-button"
          onClick={handleGenerate}
          disabled={!dataset || generating}
        >
          <FileBarChart size={18} />
          {generating ? "Generating..." : "Generate Report"}
        </button>

        {report && (
          <>
            <button
              className="upload-button secondary-button"
              onClick={() => handleDownload("pdf")}
              disabled={Boolean(downloading)}
            >
              <FileText size={16} />
              Download PDF
            </button>

            <button
              className="upload-button secondary-button"
              onClick={() => handleDownload("excel")}
              disabled={Boolean(downloading)}
            >
              <FileSpreadsheet size={16} />
              Download Excel
            </button>
          </>
        )}
      </div>

      {report && (
        <ReportPreview
          report={report}
          onDownload={handleDownload}
          downloading={downloading}
        />
      )}

      <div className="report-history">
        <h4>Report History</h4>

        {history.length === 0 && !historyLoading ? (
          <p className="muted-note">No saved reports yet.</p>
        ) : (
          <div className="table-wrapper">
            <table className="preview-table">
              <thead>
                <tr>
                  <th>Saved</th>
                  <th>Dataset</th>
                  <th>Title</th>
                  <th>Records</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {history.map((item) => (
                  <tr
                    key={item.id}
                    className={selectedId === item.id ? "row-selected" : ""}
                  >
                    <td>{formatTimestamp(item.created_at)}</td>
                    <td>{item.filename}</td>
                    <td>{item.kind === "business_report" ? "Report" : item.kind}</td>
                    <td>{item.record_count ?? "—"}</td>
                    <td>
                      <div className="history-actions">
                        <button
                          className="icon-button"
                          title="View report"
                          onClick={() => handleView(item.id)}
                          disabled={busyId !== null}
                        >
                          <Eye size={16} />
                        </button>

                        <button
                          className="icon-button"
                          title="Download PDF"
                          onClick={() => handleDownload("pdf", item.id)}
                          disabled={Boolean(downloading)}
                        >
                          <Download size={16} />
                        </button>

                        <button
                          className="icon-button"
                          title="Download Excel"
                          onClick={() => handleDownload("excel", item.id)}
                          disabled={Boolean(downloading)}
                        >
                          <FileSpreadsheet size={16} />
                        </button>

                        <button
                          className="icon-button danger"
                          title="Delete report"
                          onClick={() => handleDelete(item.id)}
                          disabled={busyId !== null}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
