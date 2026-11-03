
import React from "react";
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
  BrainCircuit
} from "lucide-react";

import "./App.css";

const salesData = [
  { name: "Laptop", sales: 120000 },
  { name: "Mobile", sales: 135000 },
  { name: "Monitor", sales: 75000 },
  { name: "Keyboard", sales: 24000 },
  { name: "Mouse", sales: 20000 }
];

const regionData = [
  { name: "North", value: 155000 },
  { name: "South", value: 135000 },
  { name: "West", value: 76000 },
  { name: "East", value: 8000 }
];

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#10b981"];

function App() {
  return (
    <div className="dashboard">

      <aside className="sidebar">
        <h2><BrainCircuit /> InsightAI</h2>

        <nav>
          <p className="active"><LayoutDashboard /> Dashboard</p>
          <p><TrendingUp /> Analytics</p>
          <p><ShoppingCart /> Sales Reports</p>
          <p><Upload /> Upload Data</p>
        </nav>

        <div className="sidebar-footer">
          AI Business Intelligence
        </div>
      </aside>

      <main className="main-content">

        <header className="navbar">
          <div>
            <h1>Business Dashboard</h1>
            <p>Welcome to your AI-powered analytics platform.</p>
          </div>

          <button className="upload-button">
            <Upload size={18} /> Upload Dataset
          </button>
        </header>

        <section className="stats-grid">

          <Stat
            title="Total Revenue"
            value="₹3,74,000"
            icon={<DollarSign />}
          />

          <Stat
            title="Total Profit"
            value="₹57,300"
            icon={<TrendingUp />}
          />

          <Stat
            title="Total Orders"
            value="10"
            icon={<ShoppingCart />}
          />

          <Stat
            title="Total Quantity"
            value="53"
            icon={<Users />}
          />

        </section>

        <section className="charts-grid">

          <div className="chart-card">
            <h3>Sales by Product</h3>

            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={salesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="sales" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-card">
            <h3>Sales by Region</h3>

            <ResponsiveContainer width="100%" height={300}>
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
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

        </section>

      </main>
    </div>
  );
}

function Stat({ title, value, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}

export default App;
