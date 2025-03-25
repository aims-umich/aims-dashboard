import os
import sqlite3
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# Database path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(ROOT_DIR, "database", "guardian.db")
DATABASE_PATH = db_path

# Define the model checkpoint
checkpoint = "kumo24/bert-sentiment-nuclear"

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

# Define label mappings
id2label = {0: "negative", 1: "neutral", 2: "positive"}
label2id = {"negative": 0, "neutral": 1, "positive": 2}

# Ensure the tokenizer has a padding token
if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})

# Load the model
model = AutoModelForSequenceClassification.from_pretrained(
    checkpoint, 
    num_labels=3, 
    id2label=id2label, 
    label2id=label2id
)

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Create a sentiment analysis pipeline
sentiment_task = pipeline(
    "sentiment-analysis",
    model=model,
    tokenizer=tokenizer,
    device=0 if torch.cuda.is_available() else -1,
    truncation=True,  # Truncate long texts
    padding=True,  # Pad shorter texts
    batch_size=8  # Process multiple texts in batches
)

def add_label_columns():
    """Adds 'label' and 'score' columns to the extracted_content table if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(extracted_content);")
    columns = [col[1] for col in cursor.fetchall()]

    if "label" not in columns:
        cursor.execute("ALTER TABLE extracted_content ADD COLUMN label TEXT;")
    if "score" not in columns:
        cursor.execute("ALTER TABLE extracted_content ADD COLUMN score REAL;")

    conn.commit()
    conn.close()
    print("Database schema updated: 'label' and 'score' columns added if missing.")

def label_extracted_text():
    """Fetches extracted sentences, applies sentiment analysis, and updates the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Fetch extracted content that hasn't been labeled
    cursor.execute("SELECT id, extracted_text FROM extracted_content WHERE label IS NULL;")
    rows = cursor.fetchall()

    if not rows:
        print("All extracted text is already labeled. No updates needed.")
        conn.close()
        return

    print(f"Found {len(rows)} unlabeled extracted sentences. Processing...")

    # Prepare data for batch processing
    batch_size = 8
    ids, texts = map(list, zip(*rows))

    labels, scores = [], []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]  # Take a batch of texts
        results = sentiment_task(batch_texts)  # Apply sentiment analysis

        # Store results
        labels.extend([res["label"] for res in results])
        scores.extend([res["score"] for res in results])

    # Update database with results
    for row_id, label, score in zip(ids, labels, scores):
        cursor.execute("""
            UPDATE extracted_content
            SET label = ?, score = ?
            WHERE id = ?;
        """, (label, score, row_id))
        conn.commit()

    print(f"Successfully labeled {len(rows)} extracted sentences.")
    conn.close()

if __name__ == "__main__":
    add_label_columns()  # Ensure the schema is updated
    label_extracted_text()  # Process and label extracted sentences
