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
  const [menuOpen, setMenuOpen] = useState(false);
  const [latestArticles, setLatestArticles] = useState([]);
  const [showAllArticles, setShowAllArticles] = useState(false);
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
      fetch('http://127.0.0.1:8000/guardian')
        .then(res => res.json())
        .then((data) => {
          setGuardianData(data);
          setLatestArticles(data.latest_articles || []);
          setError(null);

          if (data?.results) {
            const wordFrequencyBySentiment = processWordFrequencyBySentiment(data.results);
            const wordCloudData = processWordCloudData(data.results);
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

  const { 
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

  const sentimentDistData = Array.isArray(sentiment_distribution)
  ? sentiment_distribution.map(d => ({
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
      <nav className="flex items-center justify-between text-lg mb-6 relative">
        <div>
          <a href="https://www.theguardian.com/us">
            <img src="/guardian/The-Guardian-logo.png" alt="The Guardian Logo" className="h-24 block dark:hidden" />
            <img src="/guardian/The-Guardian-logo-white.png" alt="The Guardian Logo (White)" className="h-24 hidden dark:block" />
          </a>
        </div>

        {/* Hamburger Icon */}
        <button
          className="lg:hidden text-gray-700 dark:text-gray-300 focus:outline-none"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                  d={menuOpen
                    ? "M6 18L18 6M6 6l12 12"  // X icon
                    : "M4 6h16M4 12h16M4 18h16" // Hamburger icon
                  } />
          </svg>
        </button>

        {/* Menu Items */}
        <ul 
          className={`${
            menuOpen ? 'block' : 'hidden'
          } absolute top-24 left-0 w-full text-right rounded-lg bg-gray-200 dark:bg-gray-700 lg:static lg:flex lg:flex-row lg:space-x-6 lg:items-center lg:w-auto lg:bg-transparent lg:dark:bg-transparent list-none p-2 m-0 transition-all z-50`}
        >
          <li><a href="/" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Home</a></li>
          <li><a href="#overview" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Overview</a></li>
          <li><a href="#sentiment" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Sentiment Analysis</a></li>
          <li><a href="#article" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Article Analysis</a></li>
          <li><a href="#word" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Word Analysis</a></li>
          <li><a href="#list" className="block py-2 text-gray-700 dark:text-gray-300 font-bold hover:text-xl transition-all">Recent Article</a></li>
        </ul>
      </nav>

      <main className="relative z-10">
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
          <div className="h-[300px]">
            {dashboardData.wordFrequencyBySentiment?.[activeWordFrequencyTab]?.length > 0 ? (
              <>    
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
              </>
            ) : (
              <div className="w-full h-[300px]  flex items-center justify-center text-gray-500 dark:text-gray-400">
                No Word Frequency Data Available
              </div>
            )}
          </div>
        </div>

        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-200 text-center">Word Cloud</h2>
          {dashboardData.wordCloudData?.length > 0 ? (
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
          ) : (
            <div className="w-full h-[300px]  flex items-center justify-center text-gray-500 dark:text-gray-400">
              No Word Cloud Data Available
            </div>
          )}
        </div>
      </section>

      <h2 id="list" className="text-xl md:text-2xl font-semibold text-gray-800 dark:text-white mt-6 mb-4">
        Recent Articles
      </h2>
      <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
      <table className="w-full table-fixed">
        <thead className="bg-gray-100 dark:bg-gray-700">
          <tr>
            <th className="w-[10%] px-4 py-3 text-left text-sm font-medium text-gray-800 dark:text-gray-300">Date</th>
            <th className="w-[30%] px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-300">Author</th>
            <th className="w-[60%] px-4 py-3 text-left text-sm font-medium text-gray-900 dark:text-gray-300">Article</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {latestArticles.length > 0 ? (
            latestArticles
              .slice(0, showAllArticles ? latestArticles.length : 10)
              .map((article, index) => (
                <tr
                  key={index}
                  className={`${index % 2 === 0 ? 'bg-gray-10 dark:bg-gray-800' : 'bg-gray-100 dark:bg-gray-700'} hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors`}
                >
                  <td className="w-[10%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.date}</td>
                  <td className="w-[30%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.author}</td>
                  <td className="w-[60%] px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{article.title}</td>
                </tr>
            ))
          ) : (
            <tr>
              <td colSpan="3" className="px-4 py-3 text-sm text-gray-900 dark:text-gray-300 text-center">
                No articles available in the past 30 days.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {latestArticles.length > 10 && (
        <div className="text-center py-3">
          <button
            onClick={() => setShowAllArticles(!showAllArticles)}
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            {showAllArticles ? 'Show Less ▲' : 'Show More ▼'}
          </button>
        </div>
      )}
    </div>
    </main>
    </div>
  );
};

export default Guardian