import React, { useState, useEffect } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as PieTooltip,
  Legend as PieLegend,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Bar,
} from "recharts";

// Map the numeric label to text
function mapLabelToText(labelInt) {
  switch (labelInt) {
    case 0:
      return "Negative";
    case 1:
      return "Neutral";
    case 2:
      return "Positive";
    default:
      return "Unknown";
  }
}

function App() {
  // ========== 1) RECENT POSTS ==========
  const [recentPosts, setRecentPosts] = useState([]);
  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/posts/recent")
      .then((res) => res.json())
      .then((data) => {
        setRecentPosts(data);
      })
      .catch((err) => console.error("Error fetching recent posts:", err));
  }, []);

  // ========== 2) METRICS (Pie Chart / Overview) ==========
  const [metrics, setMetrics] = useState(null);
  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/metrics")
      .then((res) => res.json())
      .then((data) => {
        setMetrics(data);
      })
      .catch((err) => console.error("Error fetching metrics:", err));
  }, []);

  // ========== 3) KEYWORDS ==========
  const [keywords, setKeywords] = useState(null);
  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/keyword")
      .then((res) => res.json())
      .then((data) => {
        setKeywords(data);
      })
      .catch((err) => console.error("Error fetching keywords:", err));
  }, []);

  // ========== 4) SENTIMENT OF 0~12 MONTHS (for stacked Bar) ==========
  const [sentimentData, setSentimentData] = useState([]);
  useEffect(() => {
    const fetchAllMonths = async () => {
      const results = [];
      for (let offset = 0; offset <= 12; offset++) {
        const res = await fetch(
          `http://127.0.0.1:5000/api/sentiment/${offset}`
        );
        const data = await res.json();
        const label = `${data.year}-${String(data.month).padStart(2, "0")}`;
        let pos = data.positive || 0;
        let neg = data.negative || 0;
        let neu = data.neutral || 0;
        results.push({ label, pos, neg, neu });
      }
      // Place the most recent (offset=0) at the right end
      setSentimentData(results.reverse());
    };
    fetchAllMonths();
  }, []);

  // Colors for the Pie Chart
  const COLORS = ["#EF4444", "#6B7280", "#10B981"]; // negative=red, neutral=gray, positive=green

  // Prepare the data for the Pie Chart
  let pieData = [];
  let negativeCount = 0;
  let neutralCount = 0;
  let positiveCount = 0;

  if (metrics) {
    const {
      positiveCount: pCount,
      negativeCount: nCount,
      neutralCount: neuCount,
    } = metrics;
    negativeCount = nCount || 0;
    neutralCount = neuCount || 0;
    positiveCount = pCount || 0;
    pieData = [
      { name: "Negative", value: negativeCount },
      { name: "Neutral", value: neutralCount },
      { name: "Positive", value: positiveCount },
    ];
  }

  // === Example Overview Data ===
  // These values can be derived from the backend
  const today = new Date();
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(today.getFullYear() - 1);
  const formatYearMonth = (date) => date.toISOString().slice(0, 7);
  const timeRange = `${formatYearMonth(oneYearAgo)} to ${formatYearMonth(
    today
  )}`;

  const totalArticles = metrics
    ? metrics.positiveCount + metrics.negativeCount + metrics.neutralCount
    : 0;

  // Only display Negative Keywords and arrange them in a 3-column table
  const negativeKeywords = keywords?.negative ?? [];
  const chunkedNegatives = [];
  for (let i = 0; i < negativeKeywords.length; i += 3) {
    chunkedNegatives.push(negativeKeywords.slice(i, i + 3));
  }

  return (
    <div
      style={{
        fontFamily: "sans-serif",
        background: "#fafafa",
        margin: 0,
        padding: 0,
      }}
    >
      {/* ========== Gray background container ========== */}
      <div style={{ background: "#F3F4F6", width: "100%", padding: "1rem 0" }}>
        {/* Main Title */}
        <h1
          style={{
            fontSize: "30px",
            fontWeight: "bold",
            textAlign: "center",
            margin: "0.5rem 0",
          }}
        >
          New York Times Dashboard
        </h1>

        {/* Intro text */}
        <br />
        <p
          style={{
            textAlign: "center",
            maxWidth: "1000px",
            margin: "0 auto 1rem",
            fontSize: "20px",
          }}
        >
          This dashboard pulls nuclear-related articles from the New York Times,
          summarizes them using GPT, and analyzes sentiment
          (negative/neutral/positive). Below is an overview of the data, along
          with interactive charts and recent posts.
        </p>
        <br />

        {/* Container for overview cards and charts */}
        <div
          style={{
            maxWidth: "1800px", // Set the maximum width to 1800
            margin: "0 auto", // Center the container
            padding: "0 1rem", // Some space on the left and right
          }}
        >
          {/* ========== Overview row: includes time range, total articles, negative/neutral/positive counts ========== */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-around",
              alignItems: "center",
              marginBottom: "1rem",
              flexWrap: "wrap",
              gap: "0.5rem",
            }}
          >
            <div style={cardStyle}>
              <h3>Time Range</h3>
              <p>{timeRange}</p>
            </div>
            <div style={cardStyle}>
              <h3>Total Articles</h3>
              <p>{totalArticles}</p>
            </div>
            {/* <div style={cardStyle}>
              <h3>Total Content</h3>
              <p>{totalContent}</p>
            </div> */}
            <div style={cardStyle}>
              <h3>Negative</h3>
              <p>{negativeCount}</p>
            </div>
            <div style={cardStyle}>
              <h3>Neutral</h3>
              <p>{neutralCount}</p>
            </div>
            <div style={cardStyle}>
              <h3>Positive</h3>
              <p>{positiveCount}</p>
            </div>
          </div>

          {/* ========== Second row: PieChart + Stacked Bar ========== */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "2rem",
            }}
          >
            {/* PieChart */}
            <div
              style={{
                background: "#FEFEFE",
                padding: "1rem",
                borderRadius: "1px",
              }}
            >
              <h2
                style={{
                  fontSize: "24px",
                  fontWeight: "bold",
                  textAlign: "center",
                }}
              >
                Sentiment Distribution
              </h2>
              <br />
              {pieData.length > 0 ? (
                <PieChart width={400} height={550}>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={140}
                    label
                  >
                    {pieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <PieTooltip />
                  <PieLegend verticalAlign="bottom" />
                </PieChart>
              ) : (
                <p>Loading metrics...</p>
              )}
            </div>

            {/* Stacked Bar Chart */}
            <div
              style={{
                background: "#FEFEFE",
                padding: "3rem",
                borderRadius: "6px",
              }}
            >
              <h2
                style={{
                  fontSize: "24px",
                  fontWeight: "bold",
                  textAlign: "center",
                }}
              >
                Monthly Sentiment Distribution
                <br />
              </h2>
              <br />
              {sentimentData.length > 0 ? (
                <ComposedChart width={900} height={550} data={sentimentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="neg" stackId="a" fill="#EF4444" />
                  <Bar dataKey="neu" stackId="a" fill="#6B7280" />
                  <Bar dataKey="pos" stackId="a" fill="#10B981" />
                </ComposedChart>
              ) : (
                <p>Loading sentiment data...</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ========== Lower section: Keywords + Recent Posts (white background) ========== */}
      <div style={{ display: "flex", gap: "2rem", padding: "1rem" }}>
        {/* Left: Negative Keywords */}
        <div
          style={{
            flex: "0 0 30%",
            background: "#FFFFFF",
            padding: "1rem",
            borderRadius: "6px",
          }}
        >
          <h2
            style={{
              fontSize: "24px",
              fontWeight: "bold",
              textAlign: "center",
            }}
          >
            Top-impact keywords for each sentiment category
          </h2>
          <br />
          {keywords ? (
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
              }}
            >
              <thead>
                <tr>
                  <th>Negative</th>
                  <th>Neutral</th>
                  <th>Positive</th>
                </tr>
              </thead>
              <tbody>
                {chunkedNegatives.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row[0] || ""}</td>
                    <td>{row[1] || ""}</td>
                    <td>{row[2] || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Loading keywords...</p>
          )}
        </div>

        {/* Right: Recent Posts */}
        <div
          style={{
            flex: 1,
            background: "#FFFFFF",
            padding: "1rem",
            borderRadius: "6px",
          }}
        >
          <h2
            style={{
              fontSize: "24px",
              fontWeight: "bold",
              textAlign: "center",
            }}
          >
            Recent Posts
          </h2>
          <br />
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "left",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc" }}>
                <th style={{ padding: "8px" }}>Date</th>
                <th style={{ padding: "8px" }}>Article</th>
                <th style={{ padding: "8px" }}>Label</th>
              </tr>
            </thead>
            <tbody>
              {recentPosts.map((post) => (
                <tr key={post.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{post.date}</td>
                  <td style={{ padding: "8px" }}>{post.content}</td>
                  <td style={{ padding: "8px" }}>
                    {mapLabelToText(post.label)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// A simple card style
const cardStyle = {
  background: "#fff",
  padding: "1rem 2rem",
  borderRadius: "6px",
  textAlign: "center",
  minWidth: "220px",
};

export default App;
