import warnings
import sqlite3
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from fastapi.middleware.cors import CORSMiddleware

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
    conn = sqlite3.connect("posts.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            true_label TEXT NOT NULL,
            predicted_label TEXT NOT NULL
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

# Load the fine-tuned model
id2label = {0: "negative", 1: "neutral", 2: "positive"}
label2id = {"negative": 0, "neutral": 1, "positive": 2}

model = AutoModelForSequenceClassification.from_pretrained(
    checkpoint,
    num_labels=3,
    id2label=id2label,
    label2id=label2id
)

# Move model to GPU if available
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

# --- Step 5: Populate database with sentiment analysis results (run once) ---
def populate_db():
    conn = sqlite3.connect("posts.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts")
    count = c.fetchone()[0]
    conn.close()

    if count > 0:
        print("Database already populated. Skipping sentiment analysis.")
        return

    print("Populating database with sentiment analysis results...")
    train = pd.read_csv('./threads/training_threads.csv', quotechar='"')
    test = pd.read_csv('./threads/testing_threads.csv', quotechar='"')

    train['label'] = train.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})
    test['label'] = test.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

    all_data = pd.concat([train, test], ignore_index=True)

    results = []
    for idx, row in all_data.iterrows():
        text = row['text']
        if pd.isna(text) or text is None:
            text = ''
        else:
            text = str(text).strip()

        if not text:
            continue

        true_label = id2label[row['label']]

        try:
            predicted_label = classify_text(text)
            results.append((text, true_label, predicted_label))
        except Exception as e:
            print(f"Error processing row {idx} with text '{text}': {str(e)}")
            continue

    conn = sqlite3.connect("posts.db")
    c = conn.cursor()
    c.executemany("INSERT INTO posts (text, true_label, predicted_label) VALUES (?, ?, ?)", results)
    conn.commit()
    conn.close()
    print("Database populated successfully!")

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

@app.get("/posts/")
def get_posts():
    conn = sqlite3.connect("posts.db")
    c = conn.cursor()
    c.execute("SELECT text, true_label, predicted_label FROM posts")
    results = [{"text": row[0], "true_label": row[1], "predicted_label": row[2]} for row in c.fetchall()]
    conn.close()
    return {"results": results}

# Run the app with: uvicorn server:app --reload