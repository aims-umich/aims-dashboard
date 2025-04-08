import React, { useState, useEffect } from 'react';
import { TagCloud } from 'react-tagcloud';

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
  const [activeWordFrequencyTab, setActiveWordFrequencyTab] = useState("positive");
  const [dashboardData, setDashboardData] = useState({
    wordFrequencyBySentiment: {},
    wordCloudData: []
  });
  const [error, setError] = useState(null);

  const stopWords = new Set([
    "the", "and", "for", "with", "that", "this", "are", "was", "but", "you",
    "from", "have", "not", "they", "has", "had", "will", "can", "who", "what",
    "when", "how", "your", "all", "their", "our", "more", "about", "been",
    "one", "also", "would", "should", "could", "may", "might", "shall",
    "do", "did", "does", "done", "get", "got", "just", "said", "say",
    "says", "going", "go", "went", "come", "came", "back", "make", "made",
    "every", "any", "each", "it's", "its", "i'm", "he", "she", "it", "we",
    "them", "me", "my", "mine", "his", "hers", "him", "her", "there", "here",
    "yes", "no", "if", "then", "than", "so", "still", "because", "own", "again",
    "first", "last", "after", "before", "now", "today", "yesterday", "tomorrow",
    "into", "over", "under", "out", "in", "on", "at", "of", "as", "to", "is",
    "be", "am", "an", "a", "really", "even", "thing", "things", "someone",
    "something", "lot", "kinda", "sort", "were", "which"
  ]);

  useEffect(() => {
    Promise.all([
        fetch('http://127.0.0.1:8000/articles.json').then(res => res.json()),
        fetch('http://127.0.0.1:8000/guardian').then(res => res.json())
    ])
      .then(([articlesData, guardianData]) => {
        setArticlesByMonth(articlesData);
        setGuardianData(guardianData);
        setError(null);

        if (guardianData?.results) {
          const wordFrequencyBySentiment = processWordFrequencyBySentiment(guardianData.results);
          const wordCloudData = processWordCloudData(guardianData.results);
          setDashboardData({
            wordFrequencyBySentiment,
            wordCloudData
          });
        }

      })
      .catch((error) => {
        console.error("Error fetching data:", error);
        setError("Failed to fetch data");
      });
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

  if (!guardianData) {
    return (
      <div className="w-full h-[300px] flex items-center justify-center text-gray-500 dark:text-gray-400">
        Loading data...
      </div>
    );
  }

  // Prepare sentimentTrendData for Recharts format:
  const sentimentTrendData = Array.isArray(sentiment_trend)
  ? sentiment_trend.reduce((acc, { 'Year-Month': x, Count: y, label }) => {
      if (!x || !y || !label) return acc;
      const existing = acc.find(d => d["Year-Month"] === x);
      if (existing) {
        existing[label] = y;
      } else {
        acc.push({ "Year-Month": x, [label]: y });
      }
      return acc;
    }, [])
  : [];

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

  const processWordFrequencyBySentiment = (results) => {
    const wordFrequency = {
      positive: {},
      neutral: {},
      negative: {}
    };
  
    results.forEach((item) => {
      if (item.extracted_text && item.label) {
        const sentiment = item.label.toLowerCase();
        const words = item.extracted_text
          .toLowerCase()
          .replace(/[^\w\s]/g, "")
          .split(/\s+/);
  
        words.forEach((word) => {
          if (!stopWords.has(word) && word.length > 2) {
            if (wordFrequency[sentiment]) {
              wordFrequency[sentiment][word] = (wordFrequency[sentiment][word] || 0) + 1;
            }
          }
        });
      }
    });
  
    const wordFrequencyArrays = {};
    Object.keys(wordFrequency).forEach((sentiment) => {
      wordFrequencyArrays[sentiment] = Object.entries(wordFrequency[sentiment])
        .map(([word, count]) => ({ word, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 15);
    });
  
    return wordFrequencyArrays;
  };
  
  const processWordCloudData = (results) => {
    const wordCount = {};
  
    results.forEach((item) => {
      if (item.extracted_text) {
        const words = item.extracted_text
          .toLowerCase()
          .replace(/[^\w\s]/g, "")
          .split(/\s+/);
  
        words.forEach((word) => {
          if (!stopWords.has(word) && word.length > 2) {
            wordCount[word] = (wordCount[word] || 0) + 1;
          }
        });
      }
    });
  
    return Object.entries(wordCount)
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 50);
  };
  
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
          <li><a href="#word" className="text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Word Analysis</a></li>
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

      <h2 id="word" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Word Analysis
      </h2>
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Word Frequency by Sentiment</h2>
          <div className="h-[300px]" >    
            <div className="flex border-b mb-4">
              {["positive", "neutral", "negative"].map((label) => (
                <button
                  key={label}
                  className={`px-4 py-2 font-medium ${
                    activeWordFrequencyTab === label
                      ? label === "positive"
                        ? "text-green-600 border-b-2 border-green-600"
                        : label === "neutral"
                        ? "text-gray-600 border-b-2 border-gray-600"
                        : "text-red-600 border-b-2 border-red-600"
                      : "text-gray-500"
                  }`}
                  onClick={() => setActiveWordFrequencyTab(label)}
                >
                  {label.charAt(0).toUpperCase() + label.slice(1)}
                </button>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={dashboardData.wordFrequencyBySentiment?.[activeWordFrequencyTab] || []}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="word" width={30} tick={{ fontSize: 12, dx: -5 }} />
                <Tooltip />
                <Bar
                  dataKey="count"
                  fill={
                    activeWordFrequencyTab === "positive"
                      ? "#10B981"
                      : activeWordFrequencyTab === "neutral"
                      ? "#6B7280"
                      : "#EF4444"
                  }
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Word Cloud</h2>
            <div className="flex justify-center items-center h-[300px] overflow-hidden">
              <TagCloud
                minSize={12}
                maxSize={40}
                tags={dashboardData.wordCloudData || []}
                shuffle={true}
                className="text-center"
                randomNumberGenerator={() => Math.random()}
                renderer={(tag, size) => {
                  const fontSize = size;
                  const fontWeight = size > 30 ? "bold" : "normal";
                  const textColor =
                    size > 30 ? "#EF4444" : size > 20 ? "#6B7280" : "#A1A1AA";
                  const rotation = Math.random() * 90 - 45;

                  return (
                    <span
                      key={tag.value}
                      style={{
                        fontSize: `${fontSize}px`,
                        fontWeight: fontWeight,
                        color: textColor,
                        display: "inline-block",
                        margin: "5px",
                        transform: `rotate(${rotation}deg)`,
                        transition: "all 0.3s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.transform = `rotate(${rotation}deg) scale(1.1)`;
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.transform = `rotate(${rotation}deg) scale(1)`;
                      }}
                    >
                      {tag.value}
                    </span>
                  );
                }}
              />
            </div>
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