import warnings
import sqlite3
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

warnings.filterwarnings("ignore")

# --- Step 1: Create FastAPI application ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- Step 2: Set up SQLite database ---
def init_db():
    conn = sqlite3.connect("./threads/threads.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            true_label TEXT NOT NULL,
            predicted_label TEXT NOT NULL,
            published_on TEXT NOT NULL,
            comment_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            retweet_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Step 3: Load BERT checkpoint and model ---
checkpoint = 'kumo24/bert-sentiment-nuclear'
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})

id2label = {0: "negative", 1: "neutral", 2: "positive"}
label2id = {"negative": 0, "neutral": 1, "positive": 2}

model = AutoModelForSequenceClassification.from_pretrained(
    checkpoint,
    num_labels=3,
    id2label=id2label,
    label2id=label2id
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# --- Step 4: Function to classify text ---
def classify_text(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        predicted_class = torch.argmax(outputs.logits, dim=1).item()
    return id2label[predicted_class]

def load_and_combine_data():
    train = pd.read_csv('./threads/training_threads.csv', quotechar='"')
    test = pd.read_csv('./threads/testing_threads.csv', quotechar='"')
    all_data = pd.concat([train, test], ignore_index=True)
    all_data['published_on'] = pd.to_datetime(all_data['published_on']).dt.strftime('%Y-%m-%d')
    return all_data

def calculate_averages(df):
  return {
      "avg_comments": round(df['comment_count'].mean(), 2),
      "avg_likes": round(df['like_count'].mean(), 2),
      "avg_retweets": round(df['retweet_count'].mean(), 2)
  }

def calculate_verified_proportion(df):
    return round(df['is_verified'].mean() * 100, 2)

def get_sentiment_trends(df):
    df['published_on'] = pd.to_datetime(df['published_on'])

    date_range = pd.date_range(start='2023-01-01', end='2024-12-31', freq='2M')

    trends = {"time_periods": [], "positive": [], "negative": [], "neutral": []}

    for i in range(len(date_range) - 1):
        start_date = date_range[i]
        end_date = date_range[i + 1]

        period_df = df[(df['published_on'] >= start_date) & (df['published_on'] < end_date)]

        sentiment_counts = period_df['label'].value_counts()

        trends["time_periods"].append(f"{start_date.strftime('%Y-%m')}-{end_date.strftime('%Y-%m')}")
        trends["positive"].append(int(sentiment_counts.get(2, 0)))
        trends["negative"].append(int(sentiment_counts.get(0, 0)))
        trends["neutral"].append(int(sentiment_counts.get(1, 0)))

    return trends

# --- Step 5: Populate database with sentiment analysis results ---
def populate_db():
    conn = sqlite3.connect("./threads/threads.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts")
    count = c.fetchone()[0]
    conn.close()

    if count > 0:
        print("database was already populated")
        return

    print("populating database with sentiment analysis results...")
    all_data = load_and_combine_data()
    all_data['label'] = all_data.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

    results = []
    for idx, row in all_data.iterrows():
        text = str(row['text']).strip() if pd.notna(row['text']) else ''
        if not text:
            continue
        
        true_label = id2label[row['label']]
        predicted_label = classify_text(text)
        published_on = row['published_on']
        comment_count = int(row['comment_count']) if pd.notna(row['comment_count']) else 0
        like_count = int(row['like_count']) if pd.notna(row['like_count']) else 0
        retweet_count = int(row['retweet_count']) if pd.notna(row['retweet_count']) else 0

        results.append((text, true_label, predicted_label, published_on, comment_count, like_count, retweet_count))

    conn = sqlite3.connect("./threads/threads.db")
    c = conn.cursor()
    c.executemany(
        "INSERT INTO posts (text, true_label, predicted_label, published_on, comment_count, like_count, retweet_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
        results
    )
    conn.commit()
    conn.close()
    print("database populated successfully!")

populate_db()

# --- Step 6: FastAPI routes ---
# @app.get("/", response_class=HTMLResponse)
# def read_root():
#     html_content = """
#     <html>
#     <head><title>Sentiment Classification API</title></head>
#     <body>
#         <h1>Sentiment Classification API</h1>
#         <p>Go to <a href='/posts/'>Posts</a> for all posts (JSON).</p>
#     </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)

@app.get("/")
def get_posts():
    all_data = load_and_combine_data()
    all_data['label'] = all_data.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

    conn = sqlite3.connect("./threads/threads.db")
    c = conn.cursor()
    c.execute("SELECT text, true_label, predicted_label, published_on, comment_count, like_count, retweet_count FROM posts ORDER BY published_on ASC")
    results = [
        {
            "text": row[0],
            "true_label": row[1],
            "predicted_label": row[2],
            "published_on": row[3],
            "comment_count": row[4],
            "like_count": row[5],
            "retweet_count": row[6]
        } for row in c.fetchall()
    ]
    conn.close()
    
    averages = calculate_averages(all_data)
    verified_proportion = calculate_verified_proportion(all_data)
    sentiment_trends = get_sentiment_trends(all_data)
    
    return {
        "results": results,
        "metrics": {
            "averages": averages,
            "verified_proportion": verified_proportion,
            "sentiment_trends": sentiment_trends
        }
    }

# Run the app with: uvicorn threads:app --reload