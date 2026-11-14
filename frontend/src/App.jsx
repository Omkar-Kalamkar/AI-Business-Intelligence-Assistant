
import React, { useState, useRef } from "react";
import axios from "axios";

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
  MessageCircle
} from "lucide-react";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

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

  // Chatbot states
  const [question, setQuestion] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  // Upload dataset
  const handleUpload = async (event) => {

    const file = event.target.files[0];

    if (!file) return;

    setLoading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {

      const response = await axios.post(
        `${API_URL}/upload`,
        formData
      );

      setData(response.data);

      // Clear previous chatbot conversation
      setChatHistory([]);
      setQuestion("");

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

      const response = await axios.post(
        `${API_URL}/ask`,
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

  // Dashboard data
  const summary = data?.analysis?.summary;

  const recommendations =
    data?.analysis?.recommendations || [];

  const productData =
    data?.analysis?.product_data || [];

  const regionData =
    data?.analysis?.region_data || [];

  // Currency formatter
  const money = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(value || 0);

  return (

    <div className="dashboard">

      {/* SIDEBAR */}
      <aside className="sidebar">

        <h2>
          <BrainCircuit />
          InsightAI
        </h2>

        <nav>

          <p className="active">
            <LayoutDashboard />
            Dashboard
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

          <div>

            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              ref={fileInput}
              onChange={handleUpload}
              hidden
            />

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

              <h2>
                AI Business Recommendations
              </h2>

              {recommendations.length > 0 ? (

                <ul>

                  {recommendations.map((item, index) => (

                    <li key={index}>
                      {item}
                    </li>

                  ))}

                </ul>

              ) : (

                <p>
                  No recommendations available.
                </p>

              )}

            </section>

          </>

        )}

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
