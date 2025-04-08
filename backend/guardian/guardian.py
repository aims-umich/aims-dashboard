from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from apscheduler.schedulers.background import BackgroundScheduler
from services.scraper import GuardianScraper
from services.processor import process_articles
from services.labeler import label_extracted_text

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Connect to the SQLite database
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(ROOT_DIR, "database", "guardian.db")

UPDATE_INTERVAL = timedelta(days=3)
last_updated = None

# Ensure the database is updated
def ensure_data_is_up_to_date(force=False):
    """Check if latest 1-year data is scraped, processed, and labeled. If not, update it."""
    
    global last_updated
    now = datetime.now(timezone.utc)
    if not force and last_updated and (now - last_updated) < UPDATE_INTERVAL:
        print("Data is up-to-date. Skipping update.")
        return
    
    print("Running Guardian data update...")
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
            print(f"Scraping articles from {from_date} to {today}...")
            
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
    last_updated = now
    print("Data is up to date.")

# Schedule it every 3 days
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: ensure_data_is_up_to_date(force=True), 'interval', days=3)
scheduler.start()

# API: Guardian dashboard data
@app.get("/guardian")
def get_guardian_data():
    ensure_data_is_up_to_date()  # Trigger update on demand
    
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
    
    # Filter articles from the last 30 days
    thirty_days_ago = today - timedelta(days=30)
    latest_articles = df_unique_articles[df_unique_articles["publish_date"] >= thirty_days_ago][
        ["title", "author", "publish_date"]
    ]
    
    # Format as list of dicts
    latest_articles_data = latest_articles.sort_values(by="publish_date", ascending=False).apply(
        lambda row: {
            "title": row["title"],
            "author": row["author"],
            "date": str(row["publish_date"].date())
        },
        axis=1
    ).tolist()
    
    # Prepare result rows for frontend sentiment processing
    results = df[["extracted_text", "label"]].dropna().to_dict(orient="records")

    return {
        "sentiment_trend": df_sentiment_counts.to_dict(orient="records"),
        "sentiment_distribution": df_overall_sentiment.to_dict(orient="records"),
        "article_count": df_article_counts.to_dict(orient="records"),
        "content_count": df_content_counts.to_dict(orient="records"),
        "expected_months": expected_months,
        "latest_articles": latest_articles_data,
        "results": results,
        "overview_stats": {
            "total_articles": df_unique_articles.shape[0],
            "total_content": df.shape[0],
            "time_range_start": expected_months[0],
            "time_range_end": expected_months[-1]
        }
    }

# Run the app with: uvicorn guardian:app --reload
