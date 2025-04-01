import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';

import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

const Guardian = () => {
  const [articlesByMonth, setArticlesByMonth] = useState({});
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [guardianData, setGuardianData] = useState({
    expected_months: [],
    sentiment_trend: [],
    sentiment_distribution: [],
    article_count: [],
    content_count: [],
    overview_stats: {}
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('http://127.0.0.1:8000/articles.json')
        .then(res => {
          return res.json();
        }),
      fetch('http://127.0.0.1:8000/guardian')
        .then(res => {
          return res.json();
        })
    ])
      .then(([articlesData, guardianData]) => {
        setArticlesByMonth(articlesData);
        setGuardianData(guardianData);
        setError(null);
      })
      .catch((error) => console.error("Error fetching data:", error))
  }, []);

  const showArticles = (month) => {
    setSelectedMonth(month);
  };

  const plotLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Arial, sans-serif', size: 13, color: 'black' },
    title: { x: 0.5, font: { size: 14 } },
    autosize: true,
    margin: { l: 50, r: 50, t: 50, b: 70 },
    legend: { 
      orientation: 'h', 
      x: 0.5, 
      y: -0.6, 
      xanchor: 'center', 
      yanchor: 'top',
      font: { size: 10 }
    },
    xaxis: { 
      title: null,
      tickangle: 45,
      tickformat: '%b. %Y',
      showgrid: false,
      zeroline: false
    },
    yaxis: { 
      title: null,
      showgrid: true,
      gridcolor: 'rgba(200,200,200,0.3)',
      zeroline: false
    }
  };

  const { 
    expected_months, 
    sentiment_trend, 
    sentiment_distribution, 
    article_count, 
    content_count, 
    overview_stats 
  } = guardianData;

  // Prepare sentimentTrendData for Recharts format:
  const sentimentTrendData = sentiment_trend.reduce((acc, { 'Year-Month': x, Count: y, label }) => {
    if (!x || !y || !label) return acc;
    const existing = acc.find(d => d["Year-Month"] === x);
    if (existing) {
      existing[label] = y;
    } else {
      acc.push({ "Year-Month": x, [label]: y });
    }
    return acc;
  }, []);

  const sentimentDistData = Array.isArray(guardianData.sentiment_distribution)
  ? guardianData.sentiment_distribution.map(d => ({
      name: d.label || 'Unknown',
      value: d['Total Count'] || 0
    }))
  : [];

  const articleCountData = article_count.map(d => ({
    month: d["Year-Month"],
    count: d["Article Count"]
  }));
  
  const contentCountData = content_count.map(d => ({
    month: d["Year-Month"],
    count: d["Content Count"]
  }));
  

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200 p-4 md:p-8">
      <nav className="flex items-center justify-between text-lg mb-6">
        <div>
          <a href="https://www.theguardian.com/us">
            <img src="/guardian/The-Guardian-logo.png" alt="The Guardian Logo" className="h-24 block dark:hidden" />
            <img src="/guardian/The-Guardian-logo-white.png" alt="The Guardian Logo (White)" className="h-24 hidden dark:block" />
          </a>
        </div>
        <ul className="flex flex-row list-none p-2 justify-center m-0 space-x-6">
          <li><a href="" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Home</a></li>
          <li><a href="#overview" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Overview</a></li>
          <li><a href="#sentiment" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Sentiment Analysis</a></li>
          <li><a href="#article" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Article Analysis</a></li>
          <li><a href="#list" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Article List</a></li>
        </ul>
      </nav>

      <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white text-center mb-6">
        The Guardian Sentiment Dashboard
      </h1>
      <p className="text-base md:text-lg text-gray-700 dark:text-gray-300 leading-relaxed mb-4">
        This page presents sentiment analysis for nuclear power-related articles from The Guardian. The system collects, processes, and categorizes articles based on their sentiment—positive, neutral, or negative—towards nuclear energy. The analysis aims to provide insights into public discourse, trends, and media portrayal of nuclear power over time.
      </p>
      <p className="text-base md:text-lg text-gray-700 dark:text-gray-300 leading-relaxed mb-6">
        Through interactive visualizations, users can explore the sentiment trends, article distribution, and key statistics, helping researchers, policymakers, and the public understand the changing landscape of nuclear energy discussions.
      </p>

      <h2 id="overview" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Overview
      </h2>
      <section className="flex flex-col md:flex-row justify-between w-full gap-4">
        <p className="flex-1 text-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-200 p-4">
          <strong>Time Range:</strong> {overview_stats.time_range_start || 'N/A'} to {overview_stats.time_range_end || 'N/A'}
        </p>
        <p className="flex-1 text-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-200 p-4">
          <strong>Total Articles:</strong> {overview_stats.total_articles || 0}
        </p>
        <p className="flex-1 text-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-200 p-4">
          <strong>Total Content:</strong> {overview_stats.total_content || 0}
        </p>
      </section>

      <h2 id="sentiment" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Sentiment Analysis
      </h2>
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Sentiment Trend</h2>
          {sentimentTrendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sentimentTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="Year-Month" angle={-45} textAnchor="end" height={60} />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="positive" stroke="#10B981" strokeWidth={2} />
                <Line type="monotone" dataKey="neutral" stroke="#6B7280" strokeWidth={2} />
                <Line type="monotone" dataKey="negative" stroke="#EF4444" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-[300px] flex items-center justify-center text-gray-500 dark:text-gray-400">
              No Sentiment Trend Data Available
            </div>
          )}
        </div>

        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Sentiment Distribution</h2>
          {sentimentDistData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sentimentDistData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#6366F1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-[300px] flex items-center justify-center text-gray-500 dark:text-gray-400">
              No Sentiment Distribution Data Available
            </div>
          )}
        </div>
      </section>

      <h2 id="article" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Article Analysis
      </h2>
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
        <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Article Count</h2>
          {articleCountData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={articleCountData}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} />
                <XAxis dataKey="month" angle={-45} textAnchor="end" height={60} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-[300px] flex items-center justify-center text-gray-500 dark:text-gray-400">
              No Article Count Data Available
            </div>
          )}
        </div>

        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
        <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Content Count</h2>
          {contentCountData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
            <BarChart data={contentCountData}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} />
              <XAxis dataKey="month" angle={-45} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#6366F1" radius={[4, 4, 0, 0]} barSize={40} />
            </BarChart>
          </ResponsiveContainer>
          ) : (
            <div className="w-full h-[300px]  flex items-center justify-center text-gray-500 dark:text-gray-400">
              No Content Count Data Available
            </div>
          )}
        </div>
      </section>

      <h2 id="list" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Article List
      </h2>
      <div className="flex flex-wrap justify-between w-full gap-2 md:gap-3 mb-4">
        {expected_months.map(month => (
          <button
            key={month}
            className="flex-1 basis-[calc(100%/12-12px)] text-center rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-200 p-2 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            onClick={() => showArticles(month)}
          >
            {month}
          </button>
        ))}
      </div>
      <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full table-fixed">
          <thead className="bg-gray-100 dark:bg-gray-700">
            <tr>
              <th className="w-[10%] px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-300">Date</th>
              <th className="w-[30%] px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-300">Author</th>
              <th className="w-[60%] px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-300">Article</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {selectedMonth && articlesByMonth[selectedMonth] && articlesByMonth[selectedMonth].length > 0 ? (
              articlesByMonth[selectedMonth].map((article, index) => (
                <tr
                  key={index}
                  className={`${index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700'} hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors`}
                >
                  <td className="w-[10%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.date}</td>
                  <td className="w-[30%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.author}</td>
                  <td className="w-[60%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.title}</td>
                </tr>
              ))
            ):(
              <tr>
                <td colSpan="3" className="px-4 py-3 text-sm text-gray-900 dark:text-gray-300 text-center">
                  {selectedMonth ? 'No articles available for this month.' : 'Select a month to view articles.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Guardian