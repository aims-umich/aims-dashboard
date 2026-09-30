// Presentation details for each platform. Which platforms are live comes from the API.
export const PLATFORMS = {
  bluesky: {
    key: "bluesky",
    defaultRange: "7d",
    name: "Bluesky",
    route: "/bluesky",
    tagline: "Decentralized social network",
    description:
      "Every public Bluesky post is read from the Jetstream firehose as it is published and filtered for nuclear-energy discussion.",
    cadence: "Real time (seconds)",
    gradient: "from-sky-500 to-blue-600",
    accent: "#1185FE",
    unitLabel: "posts",
  },
  mastodon: {
    key: "mastodon",
    defaultRange: "30d",
    name: "Mastodon",
    route: "/mastodon",
    tagline: "Decentralized social network",
    description:
      "Public posts from nuclear-energy hashtag timelines on Mastodon, checked every two minutes.",
    cadence: "Every 2 minutes",
    gradient: "from-indigo-500 to-violet-600",
    accent: "#6364FF",
    credit: "Andre Gala-Garza",
    unitLabel: "posts",
  },
  reddit: {
    key: "reddit",
    defaultRange: "30d",
    name: "Reddit",
    route: "/reddit",
    tagline: "Social news and forums",
    description: "New posts from Reddit search and nuclear-energy subreddits through Reddit's official API.",
    cadence: "Every 2 minutes",
    gradient: "from-orange-500 to-red-500",
    accent: "#FF4500",
    unitLabel: "posts",
  },
  youtube: {
    key: "youtube",
    defaultRange: "all",
    name: "YouTube",
    route: "/youtube",
    tagline: "Online video sharing",
    description:
      "Comments on newly published nuclear-energy videos. New videos are found every 30 minutes and their comment threads are followed for two weeks.",
    cadence: "Every 30 minutes",
    gradient: "from-red-500 to-rose-600",
    accent: "#FF0000",
    credit: "Arvind Kutirakulam",
    unitLabel: "comments",
  },
  guardian: {
    key: "guardian",
    defaultRange: "all",
    name: "The Guardian",
    route: "/guardian",
    tagline: "British daily newspaper, US edition",
    description:
      "US news articles about nuclear power from The Guardian's Content API. Each sentence that mentions nuclear energy is scored on its own.",
    cadence: "Every 30 minutes",
    gradient: "from-emerald-500 to-teal-600",
    accent: "#052962",
    chartColor: "#4B7BC8",
    attribution: { text: "Powered by the Guardian", href: "https://open-platform.theguardian.com/" },
    listNote: "Articles are listed for 24 hours after collection. After that, only their sentiment scores are kept.",
    logo: { light: "/guardian/The-Guardian-logo.png", dark: "/guardian/The-Guardian-logo-white.png" },
    unitLabel: "sentences",
  },
  nyt: {
    key: "nyt",
    defaultRange: "all",
    name: "New York Times",
    route: "/nyt",
    tagline: "Daily newspaper based in New York City",
    description:
      "Articles about nuclear power from the New York Times Article Search API, scored on their abstract and lead paragraph.",
    cadence: "Every hour",
    gradient: "from-slate-600 to-slate-800",
    accent: "#121212",
    chartColor: "#9CA3AF",
    attribution: { text: "Data provided by The New York Times", href: "https://developer.nytimes.com/" },
    listNote: "Articles are listed for 24 hours after collection. After that, only their sentiment scores are kept.",
    unitLabel: "articles",
  },
}

export const RANGES = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All" },
]

export const PLATFORM_ORDER = ["bluesky", "mastodon", "reddit", "youtube", "guardian", "nyt"]
