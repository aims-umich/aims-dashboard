// Presentation details for each platform. Which platforms are live comes from the API.
export const PLATFORMS = {
  bluesky: {
    key: "bluesky",
    group: "social",
    name: "Bluesky",
    short: "BSKY",
    route: "/bluesky",
    defaultRange: "7d",
    description:
      "Every public Bluesky post is read from the Jetstream firehose as it is published and filtered for nuclear-energy discussion.",
    cadence: "Real time",
    unitLabel: "posts",
    unitSingular: "post",
    viewLabel: "View on Bluesky",
  },
  mastodon: {
    key: "mastodon",
    group: "social",
    name: "Mastodon",
    short: "MAST",
    route: "/mastodon",
    defaultRange: "30d",
    description: "Public posts from nuclear-energy hashtag timelines on Mastodon, checked every two minutes.",
    cadence: "Every 2 minutes",
    credit: "Andre Gala-Garza",
    unitLabel: "posts",
    unitSingular: "post",
    viewLabel: "View on Mastodon",
  },
  reddit: {
    key: "reddit",
    group: "social",
    name: "Reddit",
    short: "RDDT",
    route: "/reddit",
    defaultRange: "30d",
    description: "New posts from Reddit search and nuclear-energy subreddits through Reddit's official API.",
    cadence: "Every 2 minutes",
    unitLabel: "posts",
    unitSingular: "post",
    viewLabel: "View on Reddit",
  },
  youtube: {
    key: "youtube",
    group: "social",
    name: "YouTube",
    short: "YT",
    route: "/youtube",
    defaultRange: "30d",
    description:
      "Comments on newly published nuclear-energy videos. New videos are found every 30 minutes and their comment threads are followed for two weeks.",
    cadence: "Every 30 minutes",
    credit: "Arvind Kutirakulam",
    unitLabel: "comments",
    unitSingular: "comment",
    viewLabel: "View on YouTube",
  },
  guardian: {
    key: "guardian",
    group: "news",
    name: "The Guardian",
    short: "GUARD",
    route: "/guardian",
    defaultRange: "all",
    description:
      "Articles about nuclear power from every section of The Guardian's Content API. Each sentence that mentions nuclear energy is scored on its own; articles the Guardian tags as U.S. coverage can be shown on their own.",
    regionFilter: true,
    cadence: "Every 30 minutes",
    attribution: { text: "Powered by the Guardian", href: "https://open-platform.theguardian.com/" },
    unitLabel: "sentences",
    unitSingular: "sentence",
    articles: true,
  },
  nyt: {
    key: "nyt",
    group: "news",
    name: "New York Times",
    short: "NYT",
    route: "/nyt",
    defaultRange: "all",
    description:
      "Articles about nuclear power from the New York Times Article Search API, scored on their abstract and lead paragraph.",
    cadence: "Every hour",
    attribution: { text: "Data provided by The New York Times", href: "https://developer.nytimes.com/" },
    unitLabel: "articles",
    unitSingular: "article",
    articles: true,
  },
}

export const PLATFORM_ORDER = ["bluesky", "mastodon", "reddit", "youtube", "guardian", "nyt"]

export const RANGES = [
  { value: "24h", label: "24 hours" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "1y", label: "1 year" },
  { value: "all", label: "All" },
]

export const PAPER = {
  href: "https://www.sciencedirect.com/science/article/pii/S136403212400296X?via%3Dihub",
  authors: "Kwon, Vu, Bhargava, Radaideh, Cooper, Joynt and Radaideh",
  title:
    "Sentiment analysis of the United States public support of nuclear power on social media using large language models",
  venue: "Renewable and Sustainable Energy Reviews 200 (2024)",
}

// What the lab measured for each model it has deployed (held-out test set).
export const MODEL_ACCURACY = { "kumo24/bert-sentiment-nuclear": 0.979 }
