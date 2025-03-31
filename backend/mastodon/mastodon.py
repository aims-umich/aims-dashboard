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
import sqlite3

def init_db():
    conn = sqlite3.connect("mastodon.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            in_reply_to_id TEXT,
            in_reply_to_account_id TEXT,
            sensitive BOOLEAN,
            spoiler_text TEXT,
            visibility TEXT,
            language TEXT,
            comments_count INTEGER,
            reposts_count INTEGER,
            likes_count INTEGER,
            content TEXT,
            account TEXT,
            media_attachments TEXT,
            tags TEXT,
            application TEXT,
            reblogged BOOLEAN,
            favourited BOOLEAN,
            bookmarked BOOLEAN,
            muted BOOLEAN,
            pinned BOOLEAN,
            true_label TEXT,
            predicted_label TEXT
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
    train = pd.read_csv('./training_mastodon.csv', quotechar='"')
    test = pd.read_csv('./testing_mastodon.csv', quotechar='"')
    all_data = pd.concat([train, test], ignore_index=True)
    return all_data

def get_sentiment_trends(df):
    df['created_at'] = pd.to_datetime(df['created_at'])

    date_range = pd.date_range(start='2023-01-01', end='2024-12-31', freq='2M')

    trends = {"time_periods": [], "positive": [], "negative": [], "neutral": []}

    for i in range(len(date_range) - 1):
        start_date = date_range[i]
        end_date = date_range[i + 1]

        period_df = df[(df['created_at'] >= start_date) & (df['created_at'] < end_date)]

        sentiment_counts = period_df['label'].value_counts()

        trends["time_periods"].append(f"{start_date.strftime('%Y-%m')}-{end_date.strftime('%Y-%m')}")
        trends["positive"].append(int(sentiment_counts.get(2, 0)))
        trends["negative"].append(int(sentiment_counts.get(0, 0)))
        trends["neutral"].append(int(sentiment_counts.get(1, 0)))

    return trends

def calculate_averages(df):
  return {
      "avg_comments": round(df['comments_count'].mean(), 2),
      "avg_reposts": round(df['reposts_count'].mean(), 2),
      "avg_likes": round(df['likes_count'].mean(), 2)
  }
  
def calculate_sensitive_proportion(df):
    return round(df['sensitive'].mean() * 100, 2)

# --- Step 5: Populate database with sentiment analysis results ---
def batch_classify_texts(texts, batch_size=32):
    results = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        inputs = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
            preds = torch.argmax(outputs.logits, dim=1).cpu().numpy()
        results.extend([id2label[p] for p in preds])
    return results


def populate_db():
    conn = sqlite3.connect("mastodon.db")
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

    # Clean content and skip rows without content
    all_data['content_clean'] = all_data['content'].fillna('').apply(str).str.strip()
    all_data = all_data[all_data['content_clean'] != '']

    texts = all_data['content_clean'].tolist()
    predicted_labels = batch_classify_texts(texts)

    results = []
    for idx, row in all_data.iterrows():
        text = row['content_clean']
        true_label = id2label[row['label']]
        predicted_label = predicted_labels[idx]

        record = (
            row.get('id'),
            row.get('created_at'),
            row.get('in_reply_to_id'),
            row.get('in_reply_to_account_id'),
            row.get('sensitive', False),
            row.get('spoiler_text', ''),
            row.get('visibility'),
            row.get('language'),
            row.get('comments_count', 0),
            row.get('reposts_count', 0),
            row.get('likes_count', 0),
            text,
            str(row.get('account', '')),
            str(row.get('media_attachments', '')),
            str(row.get('tags', '')),
            str(row.get('application', '')),
            row.get('reblogged', False),
            row.get('favourited', False),
            row.get('bookmarked', False),
            row.get('muted', False),
            row.get('pinned', False),
            true_label,
            predicted_label
        )
        results.append(record)

    conn = sqlite3.connect("mastodon.db")
    c = conn.cursor()
    c.executemany("""
        INSERT INTO posts (
            id, created_at, in_reply_to_id, in_reply_to_account_id,
            sensitive, spoiler_text, visibility, language,
            comments_count, reposts_count, likes_count,
            content, account, media_attachments, tags, application,
            reblogged, favourited, bookmarked, muted, pinned,
            true_label, predicted_label
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, results)
    conn.commit()
    conn.close()
    print("database populated successfully!")

populate_db()

# --- Step 6: FastAPI routes ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
    <head><title>Sentiment Classification API</title></head>
    <body>
        <h1>Sentiment Classification API</h1>
        <p>Go to <a href='/posts/'>Posts</a> for all posts (JSON).</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/mastodon/")
def get_posts():
    conn = sqlite3.connect("mastodon.db")
    c = conn.cursor()
    df = pd.read_sql_query("""
        SELECT id, created_at, content, language, visibility, comments_count,
               reposts_count, likes_count, true_label, predicted_label, account
        FROM posts
    """, conn)

    conn.close()

    # Convert date
    df['created_at'] = pd.to_datetime(df['created_at'])

    # Basic results
    results = df.to_dict(orient='records')

    # --- METRICS ---

    # Averages
    averages = {
        "comments": df["comments_count"].mean(),
        "likes": df["likes_count"].mean(),
        "reposts": df["reposts_count"].mean()
    }

    # Verified proportion
    def is_verified(account_json):
        try:
            account_dict = eval(account_json)
            return account_dict.get('verified', False) or len(account_dict.get('fields', [])) > 0
        except:
            return False

    df['verified'] = df['account'].apply(is_verified)
    verified_proportion = df['verified'].mean()

    # Sentiment trends
    sentiment_trends = get_sentiment_trends(df)

    return {
        "results": results,
        "metrics": {
            "averages": averages,
            "verified_proportion": verified_proportion,
            "sentiment_trends": sentiment_trends
        }
    }

# Run the app with: uvicorn mastodon:app --reload
