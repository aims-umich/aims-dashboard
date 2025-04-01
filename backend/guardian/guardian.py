from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import plotly.express as px
import json
from services.scraper import GuardianScraper
from services.processor import process_articles
from services.labeler import label_extracted_text

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Connect to the SQLite database
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(ROOT_DIR, "database", "guardian.db")

# Ensure the database is updated
def ensure_data_is_up_to_date():
    """Check if latest 1-year data is scraped, processed, and labeled. If not, update it."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # **Step 1: Count articles before scraping**
    cursor.execute("SELECT COUNT(*) FROM articles;")
    articles_before = cursor.fetchone()[0]
    
    # **Step 2: Get the latest publish_date**
    cursor.execute("SELECT MAX(publish_date) FROM articles;")
    latest_date = cursor.fetchone()[0]

    # **Step 3: Define date range for scraping**
    today = datetime.today().strftime("%Y-%m-%dT%H:%M:%SZ")
    one_year_ago = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    # If no articles exist, scrape the entire past year
    if not latest_date:
        print("No articles found. Scraping the past 12 months...")
        scraper = GuardianScraper(from_date=one_year_ago, to_date=today, db_path=DATABASE_PATH)
        scraper.scrape_articles()
        
    else:
        # Convert latest_date to datetime object
        latest_date_dt = datetime.strptime(latest_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        
        # **Check if today's date is ahead of the last scraped article**
        if latest_date_dt < datetime.now(timezone.utc):
            from_date = latest_date_dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # Start from the next missing day
            print(f"Newer data available! Scraping from {from_date} to {today}...")
            
            scraper = GuardianScraper(from_date=from_date, to_date=today, db_path=DATABASE_PATH)
            scraper.scrape_articles()
        
    # **Step 4: Count articles after scraping**
    cursor.execute("SELECT COUNT(*) FROM articles;")
    articles_after = cursor.fetchone()[0]
    
    # **Step 5: If new articles were added, process them**
    if articles_after > articles_before:
        new_articles = articles_after - articles_before
        print(f"{new_articles} new articles detected! Processing nuclear-related content...")
        process_articles()
    else:
        print("No new articles found. Skipping processing step.")
   
    # **Step 6: Check if extracted nuclear content needs labeling**
    cursor.execute("SELECT COUNT(*) FROM extracted_content WHERE label IS NULL;")
    unlabeled_count = cursor.fetchone()[0]

    if unlabeled_count > 0:
        print(f"Found {unlabeled_count} unlabeled nuclear sentences! Running sentiment analysis...")
        label_extracted_text()
    else:
        print("All extracted nuclear content is already labeled.")

    conn.close()
    print("Data is up to date.")

# Ensure the database is updated before querying
ensure_data_is_up_to_date()

# Mount the static folder for assets
static_path = os.path.join(ROOT_DIR, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Load the latest 1-year data from the database
query = """
    SELECT e.id, e.article_id, a.author, a.title, a.publish_date, e.extracted_text, e.label, e.score
    FROM extracted_content e
    JOIN articles a ON e.article_id = a.id
    WHERE a.publish_date >= datetime('now', '-11 months', 'start of month')
"""
conn = sqlite3.connect(DATABASE_PATH)
df = pd.read_sql_query(query, conn)
conn.close()

# Convert publish_date to datetime and extract month/year
df["publish_date"] = pd.to_datetime(df["publish_date"], errors='coerce')
df.dropna(subset=["publish_date"], inplace=True)
df["Year-Month"] = df["publish_date"].dt.to_period("M").astype(str)

# Sort data to ensure the latest dates are displayed
df = df.sort_values(by="publish_date", ascending=False)

# Unique articles per month
df_unique_articles = df.drop_duplicates(subset=["article_id"])
df_article_counts = df_unique_articles.groupby("Year-Month").size().reset_index(name="Article Count")

# Total content count per month
df_content_counts = df.groupby("Year-Month").size().reset_index(name="Content Count")

# Sentiment distribution per month
df_sentiment_counts = df.groupby(["Year-Month", "label"]).size().reset_index(name="Count")

# Overall sentiment distribution
df_overall_sentiment = df.groupby("label").size().reset_index(name="Total Count")

# Use UTC instead of local time
today = datetime.now(timezone.utc)
expected_months = [(today.replace(day=1) - relativedelta(months=i)).strftime("%Y-%m") for i in range(0, 12)]

# Store articles by month
articles_by_month = {
    month: [
        {
            "title": row["title"],
            "author": row["author"],
            "date": str(row["publish_date"].date())
        }
        for _, row in df_unique_articles[df_unique_articles["Year-Month"] == month].iterrows()
    ]
    for month in df_unique_articles["Year-Month"].dropna().unique()
}
articles_json = json.dumps(articles_by_month, indent=4)

# Generate charts
def generate_chart(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Arial, sans-serif', size=13, color='black'),
        title=dict(x=0.5),
        autosize=False,
        width=400,
        height=225,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", x=0.5, y=-0.2, xanchor="center", yanchor="top"),
        xaxis=dict(title=None),
        yaxis=dict(title=None)
    )
    return fig.to_html(full_html=False, config={'staticPlot': True})

sentiment_trend_chart = generate_chart(
    px.line(df_sentiment_counts, x="Year-Month", y="Count", color="label", markers=True, title="Sentiment Trends")
)

sentiment_dist_chart = generate_chart(
    px.bar(df_overall_sentiment, x="label", y="Total Count", title="Sentiment Distribution")
)

article_chart = generate_chart(
    px.line(df_article_counts, x="Year-Month", y="Article Count", markers=True, title="Article Count")
)

content_chart = generate_chart(
    px.bar(df_content_counts, x="Year-Month", y="Content Count", title="Content Count")
)

# Webpage Rendering
@app.get("/", response_class=HTMLResponse)
def guardian_dashboard():
    month_buttons = "".join(f'<button onclick="showArticles(\'{month}\')">{month}</button>' for month in expected_months)
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <html>
    <head>
        <title>The Guardian Dashboard</title>
        <link rel="icon" type="image/png" href="/static/images/guardian.png">
        <link rel="stylesheet" type="text/css" href="/static/css/style.css">
        <script src="/static/js/script.js" defer></script>
    </head>
    <body>
        <nav>
            <div>
              <a href="https://www.theguardian.com/us"><img src="/static/images/The-Guardian-logo.png" alt="The Guardian Logo"></a>
            </div>
            <ul>
                <li><a href="">Home</a></li>
                <li><a href="#overview">Overview</a></li>
                <li><a href="#sentiment">Sentiment Analysis</a></li>
                <li><a href="#article">Article Analysis</a></li>
                <li><a href="#list">Article List</a></li>
            </ul>
        </nav>
        
        <h1>The Guardian Sentiment Dashboard</h1>
        <p>This page presents sentiment analysis for nuclear power-related articles from The Guardian. The system collects, processes, and categorizes articles based on their sentiment—positive, neutral, or negative—towards nuclear energy. The analysis aims to provide insights into public discourse, trends, and media portrayal of nuclear power over time.</p>
        <p>Through interactive visualizations, users can explore the sentiment trends, article distribution, and key statistics, helping researchers, policymakers, and the public understand the changing landscape of nuclear energy discussions.</p>
        
        <h2 id="overview">Overview</h2>
        <section class="section-box">
            <p><strong>Time Range:</strong> {expected_months[0]} to {expected_months[-1]}</p>
            <p><strong>Total Articles:</strong> {df_unique_articles.shape[0]}</p>
            <p><strong>Total Content:</strong> {df.shape[0]}</p>
        </section>
        
        <h2 id="sentiment">Sentiment Analysis</h2>
        <section class="chart-container">
            <div class="chart">{sentiment_trend_chart}</div>
            <div class="chart">{sentiment_dist_chart}</div>
        </section>
       
        <h2 id="article">Article Analysis</h2>
        <section class="chart-container">
            <div class="chart">{article_chart}</div>
            <div class="chart">{content_chart}</div>
        </section>
        
        <h2 id="list">Article List</h2>
        <div class="button-list">{month_buttons}</div>
        <table class="articles-table"></table>
    </body>
    </html>
    """

@app.get("/articles.json")
def get_articles_json():
    return articles_by_month

@app.get("/guardian")
def get_guardian_data():
    return {
        "sentiment_trend": df_sentiment_counts.to_dict(orient="records"),
        "sentiment_distribution": df_overall_sentiment.to_dict(orient="records"),
        "article_count": df_article_counts.to_dict(orient="records"),
        "content_count": df_content_counts.to_dict(orient="records"),
        "expected_months": expected_months,
        "overview_stats": {
            "total_articles": df_unique_articles.shape[0],
            "total_content": df.shape[0],
            "time_range_start": expected_months[0],
            "time_range_end": expected_months[-1]
        }
    }

# Run the app with: uvicorn guardian:app --reload
