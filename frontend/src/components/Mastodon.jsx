"use client"

import { useState, useEffect } from "react"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts"
import { TagCloud } from "react-tagcloud"
import Loading from "./ui/Loading"

function Mastodon() {
  const [loading, setLoading] = useState(true)
  const [dashboardData, setDashboardData] = useState({
    sentimentOverTime: [],
    sentimentDistribution: [],
    recentPosts: [],
    totalPosts: 0,
    avgComments: 0,
    avgLikes: 0,
    avgReposts: 0,
    verifiedProportion: 0,
    sentimentAccuracy: [],
    engagementTrends: [],
    wordFrequencyBySentiment: {
      positive: [],
      neutral: [],
      negative: [],
    },
    wordCloudData: [],
  })
  const [prevTotalPosts, setPrevTotalPosts] = useState(0)
  const [showNewPostsMessage, setShowNewPostsMessage] = useState(false)
  const [activeWordFrequencyTab, setActiveWordFrequencyTab] = useState("positive")

  const loadingStates = [
    { text: "Connecting to server..." },
    { text: "Fetching posts..." },
    { text: "Analyzing sentiments..." },
    { text: "Preparing dashboard..." },
  ]

  const COLORS = ["#10B981", "#6B7280", "#EF4444", "#6366F1", "#F59E0B", "#8B5CF6"]

  const stopWords = new Set(["a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself", "yourselves"])

  const fetchData = () => {
    fetch("http://127.0.0.1:8000/mastodon")
      .then((response) => response.json())
      .then((data) => {
        const results = data.results
        const totalPosts = results.length

        if (totalPosts > prevTotalPosts && prevTotalPosts !== 0) {
          setShowNewPostsMessage(true)
          setTimeout(() => setShowNewPostsMessage(false), 5000)
        }
        setPrevTotalPosts(totalPosts)

        const distributionCounts = results.reduce(
          (acc, item) => {
            acc[item.predicted_label] = (acc[item.predicted_label] || 0) + 1
            return acc
          },
          { positive: 0, neutral: 0, negative: 0 },
        )
        const sentimentDistribution = [
          { name: "Positive", value: distributionCounts.positive },
          { name: "Neutral", value: distributionCounts.neutral },
          { name: "Negative", value: distributionCounts.negative },
        ]

        const recentPosts = results.slice(-5).reverse().map((item, index) => ({
          id: `post${index + 1}`,
          content: item.content,
          sentiment: item.predicted_label.charAt(0).toUpperCase() + item.predicted_label.slice(1),
          date: new Date(item.created_at).toLocaleDateString(),
          likes: item.favourites_count || 0,
          reposts: item.reblogs_count || 0,
          comments: item.replies_count || 0,
        }))

        const sentimentAccuracy = processSentimentAccuracy(results)
        const engagementTrends = processEngagementTrends(results)
        const wordFrequencyBySentiment = processWordFrequencyBySentiment(results)
        const wordCloudData = processWordCloudData(results)

        setDashboardData({
          sentimentOverTime: data.metrics.sentiment_trends,
          sentimentDistribution,
          recentPosts,
          totalPosts,
          avgComments: data.metrics.averages.comments,
          avgReplies: data.metrics.averages.replies,
          avgFavourites: data.metrics.averages.favourites,
          avgReblogs: data.metrics.averages.reblogs,
          sentimentAccuracy,
          engagementTrends,
          wordFrequencyBySentiment,
          wordCloudData,
        })
      })
      .catch((error) => console.error("Error fetching data:", error))
      .finally(() => setLoading(false))
  }

  const processSentimentAccuracy = (results) => {
    const accuracy = { correct: 0, incorrect: 0 }

    results.forEach((post) => {
      if (post.true_label && post.predicted_label) {
        if (post.true_label === post.predicted_label) {
          accuracy.correct += 1
        } else {
          accuracy.incorrect += 1
        }
      }
    })

    return [
      { name: "Correct", value: accuracy.correct },
      { name: "Incorrect", value: accuracy.incorrect },
    ]
  }

  const processEngagementTrends = (results) => {
    const engagementByDate = {}

    results.forEach((post) => {
      if (post.created_at) {
        const date = new Date(post.created_at).toLocaleDateString()
        if (!engagementByDate[date]) {
          engagementByDate[date] = { likes: 0, comments: 0, reposts: 0, count: 0 }
        }
        engagementByDate[date].likes += post.favourites_count || 0
        engagementByDate[date].comments += post.replies_count || 0
        engagementByDate[date].reposts += post.reblogs_count || 0
        engagementByDate[date].count += 1
      }
    })

    return Object.keys(engagementByDate)
      .map((date) => ({
        date,
        likes: Math.round(engagementByDate[date].likes / engagementByDate[date].count),
        comments: Math.round(engagementByDate[date].comments / engagementByDate[date].count),
        reposts: Math.round(engagementByDate[date].reposts / engagementByDate[date].count),
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date))
  }

  const processWordFrequencyBySentiment = (results) => {
    const wordFrequency = { positive: {}, neutral: {}, negative: {} }

    results.forEach((post) => {
      if (post.content && post.predicted_label) {
        const sentiment = post.predicted_label
        const words = post.content.toLowerCase().replace(/[^\w\s]/g, "").split(/\s+/)

        words.forEach((word) => {
          if (!stopWords.has(word) && word.length > 2) {
            wordFrequency[sentiment][word] = (wordFrequency[sentiment][word] || 0) + 1
          }
        })
      }
    })

    const wordFrequencyArrays = {}
    Object.keys(wordFrequency).forEach((sentiment) => {
      wordFrequencyArrays[sentiment] = Object.entries(wordFrequency[sentiment])
        .map(([word, count]) => ({ word, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 15)
    })

    return wordFrequencyArrays
  }

  const processWordCloudData = (results) => {
    const wordCount = {}

    results.forEach((post) => {
      if (post.content) {
        const words = post.content.toLowerCase().replace(/[^\w\s]/g, "").split(/\s+/)
        words.forEach((word) => {
          if (!stopWords.has(word) && word.length > 2) {
            wordCount[word] = (wordCount[word] || 0) + 1
          }
        })
      }
    })

    return Object.entries(wordCount)
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 50)
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <>
      {loading && <Loading loadingStates={loadingStates} duration={1000} loop={true} />}
      {!loading && (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
          <header className="p-4 border-b dark:border-gray-800">
            <div className="max-w-7xl mx-auto flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Mastodon</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Andre Gala-Garza</p>
              </div>
            </div>
          </header>

          <main className="p-4">
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard title="Total Posts" value={dashboardData.totalPosts.toLocaleString()} />
                <MetricCard title="Total Keywords" value="83" />
                <MetricCard title="Avg. Replies" value={dashboardData.avgReplies.toLocaleString()} />
                <MetricCard title="Avg. Favourites" value={dashboardData.avgFavourites.toLocaleString()} />
                <MetricCard title="Avg. Reblogs" value={dashboardData.avgReblogs.toLocaleString()} />
                <MetricCard title="Percent Verified" value={`${dashboardData.verifiedProportion}%`} />
                <MetricCard title="Time Range" value="2023-2025" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Sentiment Trends</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dashboardData.sentimentOverTime}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="period" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="positive" stroke="#10B981" />
                      <Line type="monotone" dataKey="neutral" stroke="#6B7280" />
                      <Line type="monotone" dataKey="negative" stroke="#EF4444" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Sentiment Distribution</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={dashboardData.sentimentDistribution}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill="#6366F1" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Sentiment Accuracy</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={dashboardData.sentimentAccuracy}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {dashboardData.sentimentAccuracy.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Engagement Trends Over Time</h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={dashboardData.engagementTrends}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="likes" stroke="#10B981" name="Likes" />
                      <Line type="monotone" dataKey="comments" stroke="#6366F1" name="Comments" />
                      <Line type="monotone" dataKey="reposts" stroke="#F59E0B" name="Reposts" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
                    Word Frequency by Sentiment
                  </h2>
                  <div className="flex border-b mb-4">
                    <button
                      className={`px-4 py-2 font-medium ${activeWordFrequencyTab === "positive" ? "text-green-600 border-b-2 border-green-600" : "text-gray-500"}`}
                      onClick={() => setActiveWordFrequencyTab("positive")}
                    >
                      Positive
                    </button>
                    <button
                      className={`px-4 py-2 font-medium ${activeWordFrequencyTab === "neutral" ? "text-gray-600 border-b-2 border-gray-600" : "text-gray-500"}`}
                      onClick={() => setActiveWordFrequencyTab("neutral")}
                    >
                      Neutral
                    </button>
                    <button
                      className={`px-4 py-2 font-medium ${activeWordFrequencyTab === "negative" ? "text-red-600 border-b-2 border-red-600" : "text-gray-500"}`}
                      onClick={() => setActiveWordFrequencyTab("negative")}
                    >
                      Negative
                    </button>
                  </div>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart
                      data={dashboardData.wordFrequencyBySentiment[activeWordFrequencyTab]}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="word" width={80} tick={{ fontSize: 12 }} />
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

                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
                  <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Word Cloud</h2>
                  <div className="flex justify-center items-center h-[250px] overflow-hidden">
                    <TagCloud
                      minSize={12}
                      maxSize={40}
                      tags={dashboardData.wordCloudData}
                      className="text-center"
                      shuffle={true}
                      randomNumberGenerator={() => Math.random()}
                      renderer={(tag, size, color) => {
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
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
                <div className="p-4 border-b dark:border-gray-700 flex items-center">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Posts</h2>
                  {showNewPostsMessage && (
                    <span className="ml-2 text-green-600 text-sm font-medium">New Posts Found!</span>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">
                          Content
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">
                          Sentiment
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">
                          Date
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 dark:text-gray-300">
                          Engagement
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {dashboardData.recentPosts.map((post) => (
                        <tr key={post.id}>
                          <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{post.content}</td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`inline-flex px-2 py-1 rounded-full text-xs font-medium
                              ${
                                post.sentiment === "Positive"
                                  ? "bg-green-100 text-green-800"
                                  : post.sentiment === "Neutral"
                                    ? "bg-gray-100 text-gray-800"
                                    : "bg-red-100 text-red-800"
                              }`}
                            >
                              {post.sentiment}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">{post.date}</td>
                          <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">
                            {`${post.likes} likes • ${post.reposts} reposts • ${post.comments} comments`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </main>
        </div>
      )}
    </>
  )
}

function MetricCard({ title, value }) {
  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</h3>
      <div className="mt-2 flex items-baseline">
        <p className="text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  )
}

export default Mastodon
