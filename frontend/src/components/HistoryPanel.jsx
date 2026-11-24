import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Eye, History, RefreshCw, Trash2 } from "lucide-react";

import { api, downloadReport, getApiError } from "../api";
import { formatTimestamp, money } from "../format";
import BusinessInsights from "./BusinessInsights";

const KIND_LABELS = {
  upload_analysis: "Upload analysis",
  business_insights: "Business insights"
};

export default function HistoryPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [reportingId, setReportingId] = useState(null);
  const loadRequest = useRef(false);
  const detailRequest = useRef(false);

  const fetchHistory = useCallback(async () => {
    const response = await api.get("/history");
    return response.data.items || [];
  }, []);

  const loadHistory = useCallback(async () => {
    if (loadRequest.current) return;

    loadRequest.current = true;
    setLoading(true);
    setError("");

    try {
      setItems(await fetchHistory());
    } catch (err) {
      setError(getApiError(err, "Unable to load insight history."));
    } finally {
      loadRequest.current = false;
      setLoading(false);
    }
  }, [fetchHistory]);

  useEffect(() => {
    let active = true;

    fetchHistory()
      .then((historyItems) => {
        if (active) {
          setItems(historyItems);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(getApiError(err, "Unable to load insight history."));
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [fetchHistory]);

  const viewInsight = async (id) => {
    if (detailRequest.current) return;

    detailRequest.current = true;
    setDetailLoading(true);
    setError("");

    try {
      const response = await api.get(`/history/${id}`);
      setSelected(response.data);
    } catch (err) {
      setError(getApiError(err, "Unable to load this insight."));
    } finally {
      detailRequest.current = false;
      setDetailLoading(false);
    }
  };

  const deleteInsight = async (id) => {
    if (deletingId !== null) return;

    setDeletingId(id);
    setError("");

    try {
      await api.delete(`/history/${id}`);
      if (selected?.id === id) setSelected(null);
      await loadHistory();
    } catch (err) {
      setError(getApiError(err, "Unable to delete this insight."));
    } finally {
      setDeletingId(null);
    }
  };

  const downloadInsightReport = async (id) => {
    if (reportingId !== null) return;

    setReportingId(id);
    setError("");

    try {
      await downloadReport(id);
    } catch (err) {
      setError(getApiError(err, "Unable to download the PDF report."));
    } finally {
      setReportingId(null);
    }
  };

  const payload = selected?.payload;
  const isFullInsight = payload && "anomalies" in payload;
  const uploadSummary = payload?.analysis?.summary;

  return (
    <section className="chart-card history-panel" id="insight-history">
      <div className="panel-header">
        <h3>
          <History size={18} /> Insight History
        </h3>

        <button
          className="upload-button secondary-button"
          onClick={loadHistory}
          disabled={loading}
        >
          <RefreshCw size={16} />
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <p className="muted-note">
        Previous analysis results with timestamps and dataset
        references. Select an entry to revisit it.
      </p>

      {error && <p className="error-message">{error}</p>}

      {items.length === 0 && !loading ? (
        <p className="muted-note">
          No saved insights yet. Upload a dataset to create one.
        </p>
      ) : (
        <div className="table-wrapper">
          <table className="preview-table">
            <thead>
              <tr>
                <th>Saved</th>
                <th>Dataset</th>
                <th>Type</th>
                <th>Records</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={
                    selected?.id === item.id ? "row-selected" : ""
                  }
                >
                  <td>{formatTimestamp(item.created_at)}</td>
                  <td>{item.filename}</td>
                  <td>{KIND_LABELS[item.kind] || item.kind}</td>
                  <td>{item.record_count ?? "—"}</td>
                  <td>
                    <div className="history-actions">
                      <button
                        className="icon-button"
                        title="View insight"
                        onClick={() => viewInsight(item.id)}
                        disabled={detailLoading}
                      >
                        <Eye size={16} />
                      </button>

                      <button
                        className="icon-button"
                        title="Download PDF report"
                        onClick={() => downloadInsightReport(item.id)}
                        disabled={reportingId !== null}
                      >
                        <Download size={16} />
                      </button>

                      <button
                        className="icon-button danger"
                        title="Delete insight"
                        onClick={() => deleteInsight(item.id)}
                        disabled={deletingId !== null}
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

      {detailLoading && (
        <p className="muted-note">Loading saved insight...</p>
      )}

      {selected && isFullInsight && (
        <div className="history-snapshot">
          <h4>
            Snapshot: {selected.filename} (
            {formatTimestamp(selected.created_at)})
          </h4>

          <BusinessInsights
            insights={payload}
            showRefresh={false}
          />
        </div>
      )}

      {selected && !isFullInsight && uploadSummary && (
        <div className="history-snapshot">
          <h4>
            Snapshot: {selected.filename} (
            {formatTimestamp(selected.created_at)})
          </h4>

          <div className="period-summary">
            <div>
              <p className="muted-note">Total sales</p>
              <strong>{money(uploadSummary.total_sales)}</strong>
            </div>
            <div>
              <p className="muted-note">Total profit</p>
              <strong>{money(uploadSummary.total_profit)}</strong>
            </div>
            <div>
              <p className="muted-note">Records</p>
              <strong>{uploadSummary.total_records}</strong>
            </div>
          </div>

          <ul className="snapshot-insights">
            {(payload.analysis.insights || []).map((insight, index) => (
              <li key={index}>{insight}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
