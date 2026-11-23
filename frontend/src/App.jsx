
import { useState, useRef } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";

import {
  LayoutDashboard,
  TrendingUp,
  ShoppingCart,
  DollarSign,
  Users,
  Upload,
  BrainCircuit,
  Send,
  MessageCircle,
  Lightbulb,
  History,
  Bell
} from "lucide-react";

import { api } from "./api";
import { money } from "./format";
import BusinessInsights from "./components/BusinessInsights";
import HistoryPanel from "./components/HistoryPanel";

import "./App.css";

const COLORS = [
  "#6366f1",
  "#06b6d4",
  "#f59e0b",
  "#10b981",
  "#ec4899"
];

function App() {
  // Dashboard states
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fileInput = useRef(null);

  // Business insights states
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [activeNav, setActiveNav] = useState("dashboard");

  // Chatbot states
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  // Dataset comparison states
  const [dimension, setDimension] = useState("product");
  const [item1, setItem1] = useState("Mobile");
  const [item2, setItem2] = useState("Laptop");
  const [comparison, setComparison] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const scrollToSection = (id, navKey) => {
    setActiveNav(navKey);

    if (id === "top") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    document
      .getElementById(id)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Fetch advanced business insights
  const fetchInsights = async () => {
    setInsightsLoading(true);

    try {
      const response = await api.get("/insights");
      setInsights(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to generate business insights."
      );
    } finally {
      setInsightsLoading(false);
    }
  };

  // Upload dataset
  const handleUpload = async (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await api.post(
        "/upload",
        formData
      );

      setData(response.data);

      // Reset chatbot and comparison after uploading new data
      setChatHistory([]);
      setQuestion("");
      setComparison(null);
      setInsights(null);

      await fetchInsights();

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to upload dataset."
      );

    } finally {
      setLoading(false);
      event.target.value = "";
    }
  };

  // Chatbot API connection
  const handleAsk = async () => {
    const userQuestion = question.trim();

    if (!userQuestion || chatLoading) return;

    if (!data) {
      setError("Please upload a dataset first.");
      return;
    }

    setError("");
    setChatLoading(true);
    setQuestion("");

    try {
      const response = await api.post(
        "/ask",
        {
          question: userQuestion
        }
      );

      setChatHistory((prev) => [
        ...prev,
        {
          question: userQuestion,
          answer: response.data.answer
        }
      ]);

    } catch (err) {
      const message =
        err.response?.data?.detail ||
        "Unable to get an answer.";

      setChatHistory((prev) => [
        ...prev,
        {
          question: userQuestion,
          answer: message
        }
      ]);

    } finally {
      setChatLoading(false);
    }
  };

  // Compare two products or regions
  const handleCompare = async () => {
    if (!data) {
      setError("Please upload a dataset first.");
      return;
    }

    if (!item1.trim() || !item2.trim()) {
      setError("Please enter both items to compare.");
      return;
    }

    if (
      item1.trim().toLowerCase() ===
      item2.trim().toLowerCase()
    ) {
      setError("Please select two different items.");
      return;
    }

    setCompareLoading(true);
    setError("");
    setComparison(null);

    try {
      const response = await api.post(
        "/compare",
        {
          dimension: dimension,
          item1: item1.trim(),
          item2: item2.trim()
        }
      );

      setComparison(response.data);

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to compare the selected items."
      );

    } finally {
      setCompareLoading(false);
    }
  };

  // Dashboard data
  const summary = data?.analysis?.summary;

  const recommendations =
    data?.analysis?.recommendations || [];

  const productData =
    data?.analysis?.product_data || [];

  const regionData =
    data?.analysis?.region_data || [];

  
// Dataset preview
  const previewData = data?.preview || [];

  const previewColumns =
    previewData.length > 0
      ? Object.keys(previewData[0])
      : [];

  const alertCount = insights?.kpi_alerts?.alerts?.length || 0;

  return (
    <div className="dashboard">

      {/* SIDEBAR */}
      <aside className="sidebar">

        <h2>
          <BrainCircuit />
          InsightAI
        </h2>

        <nav>
          <p
            className={activeNav === "dashboard" ? "active" : ""}
            onClick={() => scrollToSection("top", "dashboard")}
          >
            <LayoutDashboard />
            Dashboard
          </p>

          <p
            className={activeNav === "insights" ? "active" : ""}
            onClick={() =>
              scrollToSection("business-insights", "insights")
            }
          >
            <Lightbulb />
            Business Insights
          </p>

          <p
            className={activeNav === "history" ? "active" : ""}
            onClick={() =>
              scrollToSection("insight-history", "history")
            }
          >
            <History />
            Insight History
          </p>

          <p>
            <TrendingUp />
            Analytics
          </p>

          <p>
            <ShoppingCart />
            Sales Reports
          </p>

          <p onClick={() => fileInput.current?.click()}>
            <Upload />
            Upload Data
          </p>
        </nav>

        <div className="sidebar-footer">
          AI Business Intelligence
        </div>

      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">

        {/* NAVBAR */}
        <header className="navbar">

          <div>
            <h1>Business Dashboard</h1>

            <p>
              Welcome to your AI-powered analytics platform.
            </p>

            {data && (
              <p>
                Dataset: {data.filename}
              </p>
            )}
          </div>

          <div className="navbar-actions">
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              ref={fileInput}
              onChange={handleUpload}
              hidden
            />

            {alertCount > 0 && (
              <button
                className="alert-bell"
                title={`${alertCount} KPI alert(s) — click to review`}
                onClick={() =>
                  scrollToSection("kpi-alerts", "insights")
                }
              >
                <Bell size={20} />
                <span className="alert-bell-count">
                  {alertCount}
                </span>
              </button>
            )}

            <button
              className="upload-button"
              onClick={() => fileInput.current?.click()}
              disabled={loading}
            >
              <Upload size={18} />
              {loading ? "Analyzing..." : "Upload Dataset"}
            </button>
          </div>

        </header>

        {/* ERROR MESSAGE */}
        {error && (
          <p className="error-message">
            {error}
          </p>
        )}

        {/* WELCOME SCREEN */}
        {!data && !loading && (
          <div className="chart-card">
            <h3>Welcome to InsightAI</h3>

            <p>
              Upload a CSV or Excel dataset to generate
              your business analytics dashboard.
            </p>
          </div>
        )}

        {/* DASHBOARD */}
        {summary && (
          <>
            {/* KPI CARDS */}
            <section className="stats-grid">

              <Stat
                title="Total Revenue"
                value={money(summary.total_sales)}
                icon={<DollarSign />}
              />

              <Stat
                title="Total Profit"
                value={money(summary.total_profit)}
                icon={<TrendingUp />}
              />

              <Stat
                title="Total Orders"
                value={summary.total_records}
                icon={<ShoppingCart />}
              />

              <Stat
                title="Total Quantity"
                value={summary.total_quantity}
                icon={<Users />}
              />

            </section>

            {/* CHARTS */}
            <section className="charts-grid">

              {/* PRODUCT SALES CHART */}
              <div className="chart-card">

                <h3>Sales by Product</h3>

                {productData.length > 0 ? (
                  <ResponsiveContainer
                    width="100%"
                    height={300}
                  >
                    <BarChart data={productData}>
                      <CartesianGrid strokeDasharray="3 3" />

                      <XAxis dataKey="name" />
                      <YAxis />

                      <Tooltip
                        formatter={(value) => money(value)}
                      />

                      <Bar
                        dataKey="sales"
                        fill="#6366f1"
                        radius={[6, 6, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p>No product information available.</p>
                )}

              </div>

              {/* REGION SALES CHART */}
              <div className="chart-card">

                <h3>Sales by Region</h3>

                {regionData.length > 0 ? (
                  <ResponsiveContainer
                    width="100%"
                    height={300}
                  >
                    <PieChart>
                      <Pie
                        data={regionData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={100}
                        label
                      >
                        {regionData.map((entry, index) => (
                          <Cell
                            key={entry.name}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </Pie>

                      <Tooltip
                        formatter={(value) => money(value)}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p>No region information available.</p>
                )}

              </div>

            </section>

            {/* BUSINESS INSIGHTS */}
            <section className="chart-card insights-card">

              <h3>Business Insights</h3>

              <p>
                Total Records: {summary.total_records}
              </p>

              <p>
                Missing Values: {summary.missing_values}
              </p>

              <p>
                Duplicate Records: {summary.duplicate_records}
              </p>

              {(data.analysis.insights || []).map(
                (insight, index) => (
                  <p key={index}>
                    • {insight}
                  </p>
                )
              )}

            </section>

            {/* AI BUSINESS RECOMMENDATIONS */}
            <section className="recommendations-container">

              <h2>AI Business Recommendations</h2>

              {recommendations.length > 0 ? (
                <ul>
                  {recommendations.map((item, index) => (
                    <li key={index}>
                      {item}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No recommendations available.</p>
              )}

            </section>

            {/* ADVANCED BUSINESS INSIGHTS */}
            {insightsLoading && (
              <p className="muted-note">
                Detecting anomalies and generating insights...
              </p>
            )}

            <BusinessInsights
              insights={insights}
              onRefresh={fetchInsights}
              refreshing={insightsLoading}
            />
          </>
        )}


{/* DATASET PREVIEW */}
{data && (
<section className="chart-card dataset-preview">
  <h2>Dataset Preview</h2>
  <p>
    Showing the first {previewData.length} records from {data.filename}.
  </p>

  {previewData.length > 0 ? (
    <div className="table-wrapper">
      <table className="preview-table">
        <thead>
          <tr>
            {previewColumns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {previewData.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {previewColumns.map((column) => (
                <td key={column}>{row[column] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <p>No preview data available.</p>
  )}
</section>
)}


        {/* DATASET COMPARISON SECTION */}
        <section className="comparison-container">

          <h2>Compare Business Performance</h2>

          <div className="comparison-controls">

            <select
              value={dimension}
              onChange={(e) => {
                setDimension(e.target.value);
                setComparison(null);

                if (e.target.value === "product") {
                  setItem1("Mobile");
                  setItem2("Laptop");
                } else {
                  setItem1("North");
                  setItem2("South");
                }
              }}
            >
              <option value="product">Compare Products</option>
              <option value="region">Compare Regions</option>
            </select>

            <input
              type="text"
              placeholder="Enter first item"
              value={item1}
              onChange={(e) => setItem1(e.target.value)}
            />

            <input
              type="text"
              placeholder="Enter second item"
              value={item2}
              onChange={(e) => setItem2(e.target.value)}
            />

            <button
              onClick={handleCompare}
              disabled={compareLoading || !data}
            >
              {compareLoading ? "Comparing..." : "Compare"}
            </button>

          </div>

          {comparison && (
            <div className="comparison-result">

              <h3>Comparison Result</h3>

              {comparison.comparison.map((item) => (
                <p key={item.name}>
                  <strong>{item.name}:</strong>{" "}
                  {money(item.sales)}
                </p>
              ))}

              <p>
                <strong>Difference:</strong>{" "}
                {money(comparison.difference)}
              </p>

              <p>
                <strong>Higher Performer:</strong>{" "}
                {comparison.higher_performer}
              </p>

            </div>
          )}

        </section>

        {/* AI CHATBOT */}
        <section className="chatbot-container">

          <h2>
            <MessageCircle size={22} />
            AI Business Assistant
          </h2>

          <div className="chat-history">

            {chatHistory.length === 0 && (
              <p>
                Ask me anything about your sales data!
              </p>
            )}

            {chatHistory.map((chat, index) => (
              <div
                key={index}
                className="chat-message"
              >
                <p>
                  <strong>You:</strong> {chat.question}
                </p>

                <p>
                  <strong>AI:</strong> {chat.answer}
                </p>
              </div>
            ))}

            {chatLoading && (
              <p>
                AI is analyzing your question...
              </p>
            )}

          </div>

          {/* CHAT INPUT */}
          <div className="chat-input">

            <input
              type="text"
              placeholder="Ask a question about your data..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleAsk();
                }
              }}
            />

            <button
              onClick={handleAsk}
              disabled={!question.trim() || chatLoading}
            >
              <Send size={16} />
              {chatLoading ? "Thinking..." : "Send"}
            </button>

          </div>

        </section>

        {/* INSIGHT HISTORY */}
        <HistoryPanel />

      </main>
    </div>
  );
}

// KPI CARD COMPONENT
function Stat({ title, value, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">
        {icon}
      </div>

      <p>{title}</p>

      <h2>{value}</h2>
    </div>
  );
}

export default App;
