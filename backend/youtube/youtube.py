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
from sklearn.model_selection import train_test_split

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
    conn = sqlite3.connect("youtube.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            true_label TEXT NOT NULL,
            predicted_label TEXT NOT NULL,
            published_on TEXT NOT NULL,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            video_id TEXT NOT NULL
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

# --- Step 5: Load and split dataset ---
def load_and_split_data():
    data = pd.read_csv("Youtube_Label.csv", quotechar='"')

    # Ensure required columns exist
    required_columns = {'comment_text', 'Sentiment', 'published_at', 'like_count', 'comment_count'}
    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise KeyError(f"Missing columns in CSV: {missing_columns}")

    # Rename columns to match expected names
    data.rename(columns={'published_at': 'published_on', 'Sentiment': 'label', 'comment_text': 'text'}, inplace=True)

    # Convert 'published_on' to proper date format
    data['published_on'] = pd.to_datetime(data['published_on'], errors='coerce').dt.strftime('%Y-%m-%d')

    # Fill NaN values with defaults
    data['text'] = data['text'].fillna('')
    data['like_count'] = data['like_count'].fillna(0).astype(int)
    data['comment_count'] = data['comment_count'].fillna(0).astype(int)

    train, test = train_test_split(data, test_size=0.2, random_state=42)
    return train, test



def calculate_averages(df):
  return {
      "avg_comments": round(df['comment_count'].mean(), 2),
      "avg_likes": round(df['like_count'].mean(), 2)
  }

def get_youtube_trends(df):
    df['published_on'] = pd.to_datetime(df['published_on'])

    date_range = pd.date_range(start='2022-01-01', end='2024-12-31', freq='2M')

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

# --- Step 6: Populate database with sentiment analysis results ---
def populate_db():
    conn = sqlite3.connect("youtube.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM videos")
    count = c.fetchone()[0]
    conn.close()

    if count > 0:
        print("Database was already populated.")
        return

    print("Populating database with sentiment analysis results...")
    train, test = load_and_split_data()
    all_data = pd.concat([train, test], ignore_index=True)
    all_data['label'] = all_data.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

    results = []
    for _, row in all_data.iterrows():
        text = str(row['text']).strip() if pd.notna(row['text']) else ''
        if not text:
            continue
        
        true_label = id2label[row['label']]
        predicted_label = classify_text(text)
        published_on = row['published_on']
        like_count = int(row['like_count']) if pd.notna(row['like_count']) else 0
        comment_count = int(row['comment_count']) if pd.notna(row['comment_count']) else 0

        video_id = row['video_id'] if 'video_id' in row and pd.notna(row['video_id']) else ''
        results.append((text, true_label, predicted_label, published_on, like_count, comment_count, video_id))

    conn = sqlite3.connect("youtube.db")
    c = conn.cursor()
    c.executemany(
        "INSERT INTO videos (text, true_label, predicted_label, published_on, like_count, comment_count, video_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        results
    )

    conn.commit()
    conn.close()
    print("Database populated successfully!")

populate_db()

# --- Step 7: FastAPI routes ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
    <head><title>YouTube Sentiment API</title></head>
    <body>
        <h1>YouTube Sentiment API</h1>
        <p>Go to <a href='/videos/'>Videos</a> for sentiment data (JSON).</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/videos/")
def get_videos():
    train, test = load_and_split_data()
    all_data = pd.concat([train, test], ignore_index=True)
    all_data['label'] = all_data.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

    conn = sqlite3.connect("youtube.db")
    c = conn.cursor()
    c.execute("SELECT text, true_label, predicted_label, published_on, like_count, comment_count, video_id FROM videos ORDER BY published_on ASC")

    results = [
    {
        "text": row[0],
        "true_label": row[1],
        "predicted_label": row[2],
        "published_on": row[3],
        "like_count": row[4],
        "comment_count": row[5],
        "video_id": row[6]
    } for row in c.fetchall()
    ]
    conn.close()
    
    averages = calculate_averages(all_data)
    sentiment_trends = get_youtube_trends(all_data)
    
    return {
        "results": results,
        "metrics": {
            "averages": averages,
            "sentiment_trends": sentiment_trends
        }
    }

# Run the app with: uvicorn youtube:app --reload