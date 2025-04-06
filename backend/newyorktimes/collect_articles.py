import datetime
import sqlite3

import torch
import pandas as pd
from pynytimes import NYTAPI
from openai import AzureOpenAI
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import time
import os
import schedule
from dotenv import load_dotenv

DB_PATH = "var/dashdb.sqlite3"

NYT_API_KEY = os.getenv("NYT_API_KEY")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

checkpoint = 'kumo24/bert-sentiment-nuclear'
tokenizer = AutoTokenizer.from_pretrained(checkpoint)

# If the tokenizer has no pad token, add '[PAD]'
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


def classify_text(text: str) -> str:
    """
    Returns 'negative' / 'neutral' / 'positive'.
    """
    inputs = tokenizer(text, return_tensors="pt",
                       padding=True, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        pred_idx = torch.argmax(outputs.logits, dim=1).item()

    return id2label[pred_idx]


def label_nuclear_attitude_bert():
    """
    Connect to the SQLite database and do the following:
    1. Delete records where content = "Not related." (or similar irrelevant text)
    2. Find all rows with label IS NULL
    3. Use the local BERT model classify_text() to label them (0=negative,1=neutral,2=positive)
    4. Update the database with these labels
    """

    # (1) Open the database
    conn = sqlite3.connect('var/dashdb.sqlite3')
    c = conn.cursor()

    # (2) Remove irrelevant records
    delete_sql = """
        DELETE FROM records
        WHERE content = 'Not related.'
           OR content = 'The text is related to "nuclear".'
    """
    c.execute(delete_sql)
    deleted_rows = c.rowcount
    print(f"Deleted {deleted_rows} rows where content='Not related.'")

    # (3) Select all rows where label IS NULL
    select_sql = """
        SELECT id, content
        FROM records
        WHERE label IS NULL
    """
    c.execute(select_sql)
    rows_to_label = c.fetchall()
    print(f"Found {len(rows_to_label)} rows to label.")

    if not rows_to_label:
        print("No rows need labeling. Done.")
        conn.commit()
        conn.close()
        return

    # Prepare update statement for label
    update_sql = """
        UPDATE records
        SET label = ?
        WHERE id = ?
    """

    # (4) Loop through each row, use local BERT to classify, update DB
    for row in rows_to_label:
        row_id, content_text = row
        try:
            # Could be 'negative'/'neutral'/'positive'
            label_str = classify_text(content_text)
            label_int = label2id[label_str]
            c.execute(update_sql, (label_int, row_id))
        except Exception as e:
            print(f"[BERT Error] row_id={row_id}, error: {e}")
            # You can decide whether to keep label=NULL or something else if error
            pass

        # Optional slight delay
        time.sleep(0.05)

    # (5) Commit & close
    conn.commit()
    conn.close()
    print("All done. Database updated with nuclear attitude labels (local BERT).")


def label_nuclear_attitude(azure_api_key: str):
    """
    Connect to the SQLite database and do the following:
    1. Delete records where content = "Not related."
    2. Find all rows where label IS NULL, call GPT to label with (neutral/negative/positive)
       and store them as integers (0,1,2)
    """

    # Keep consistent with earlier code or BERT usage
    label2id = {
        "negative": 0,
        "neutral": 1,
        "positive": 2
    }

    # (1) Connect & remove records with 'Not related.'
    conn = sqlite3.connect('var/dashdb.sqlite3')
    c = conn.cursor()

    delete_sql = """
        DELETE FROM records
        WHERE content = 'Not related.'
        OR content = 'The text is related to "nuclear".'
    """
    c.execute(delete_sql)
    deleted_rows = c.rowcount
    print(f"Deleted {deleted_rows} rows where content='Not related.'")

    # (2) Retrieve rows with label IS NULL
    select_sql = """
        SELECT id, content
        FROM records
        WHERE label IS NULL
    """
    c.execute(select_sql)
    rows_to_label = c.fetchall()
    print(f"Found {len(rows_to_label)} rows to label.")

    if not rows_to_label:
        print("No rows need labeling. Done.")
        conn.commit()
        conn.close()
        return

    # (3) Initialize GPT client (AzureOpenAI)
    client = AzureOpenAI(
        api_key=azure_api_key,
        api_version="2024-06-01",
        azure_endpoint="https://api.umgpt.umich.edu/azure-openai-api",
        organization="372598"
    )

    system_prompt = (
        "You are an AI that identifies attitudes toward nuclear. "
        "You must respond with only one of the following: neutral, negative, or positive"
        "Base your answer strictly on the text provided."
    )

    # (4) Loop and call GPT to label each row
    update_sql = """
        UPDATE records
        SET label = ?
        WHERE id = ?
    """

    for row in rows_to_label:
        row_id, content_text = row

        user_prompt = (
            f"Based on the following text, does it shift people's attitude toward nuclear "
            f"in a more positive, negative, or remain neutral direction?\n\n{content_text}\n\n"
            "Please respond with exactly one word: neutral, negative, or positive."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-35-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            label_text = response.choices[0].message.content.strip().lower()
            if label_text not in label2id:
                print(
                    f"GPT returned unexpected label '{label_text}'. Forcing to 'neutral'.")
                label_text = "neutral"

            label_int = label2id[label_text]
            c.execute(update_sql, (label_int, row_id))

        except Exception as e:
            print(f"[GPT Error] row_id={row_id}, error: {e}")
            # Decide if label stays NULL or becomes something else
            pass

        time.sleep(0.05)

    conn.commit()
    conn.close()
    print("All done. Database updated with nuclear attitude labels.")


def gpt_summarize(azure_api_key: str, content_text: str) -> str:
    gpt_client = AzureOpenAI(
        api_key=azure_api_key,
        api_version="2024-06-01",
        azure_endpoint="https://api.umgpt.umich.edu/azure-openai-api",
        organization="372598"
    )
    system_prompt = (
        "Please analyze the following text (Title, Abstract, Snippet, Lead Paragraph). "
        "If the content is not related to \"nuclear\" at all, output \"Not related\". "
        "Otherwise, provide a summary focusing on the keyword \"nuclear\" in about 130 words."
    )

    try:
        response = gpt_client.chat.completions.create(
            model="gpt-35-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_text}
            ],
            temperature=0,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT Error] {e}")
        return "(GPT error) Unable to summarize."


class ArticleSearcher:
    def __init__(self, nyt_api_key: str, azure_openai_key: str):
        self.nyt_api_key = nyt_api_key
        self.azure_openai_key = azure_openai_key
        self.nyt = NYTAPI(nyt_api_key, parse_dates=True)

    def collect_summarized_articles_at_date(self, start_date: datetime.datetime):
        """
        Single call to article_search; set results=500 (up to 500 articles).
        The library auto-paginates with 10 items per page until filled or no more data.
        """
        # (1) We don't check if DB exists. Just open the connection
        conn = sqlite3.connect('var/dashdb.sqlite3')
        c = conn.cursor()

        # (2) Try up to 100 results. The library auto pages
        articles = self.nyt.article_search(
            query="nuclear",
            results=100,
            dates={
                "begin": start_date,
                "end": start_date
            },
            options={
                "sort": "oldest",
                "fq": 'body:("nuclear")'
            }
        )
        print(f"Got {len(articles)} articles from NYT.")

        total_inserted = 0
        for article in articles:
            pub_date_str = self._extract_pub_date_str(article)
            if not pub_date_str:
                continue

            # (3) Combine article fields
            content_text = self._get_article_text(article)

            # (4) Summarize with GPT
            summary_text = gpt_summarize(self.azure_openai_key, content_text)

            # (5) Insert into DB (optionally do local BERT classification if desired)
            c.execute(
                "INSERT INTO records (date, content) VALUES (?, ?)",
                (pub_date_str, summary_text)
            )
            total_inserted += 1

        conn.commit()
        conn.close()
        print(f"Done. Inserted {total_inserted} articles into DB.")

    def collect_summarized_articles_after_date(self, start_date: datetime.datetime):
        """
        Single call to article_search; set results=500 (up to 500 articles).
        The library auto-paginates with 10 items per page until filled or no more data.
        """
        # (1) We don't check if DB exists
        conn = sqlite3.connect('var/dashdb.sqlite3')
        c = conn.cursor()

        # (2) Try up to 100 results
        articles = self.nyt.article_search(
            query="nuclear",
            results=100,
            dates={
                "begin": start_date,
            },
            options={
                "sort": "oldest",
                "fq": 'body:("nuclear")'
            }
        )
        print(f"Got {len(articles)} articles from NYT.")

        total_inserted = 0
        for article in articles:
            pub_date_str = self._extract_pub_date_str(article)
            if not pub_date_str:
                continue

            # (3) Combine article fields
            content_text = self._get_article_text(article)

            # (4) Summarize with GPT
            summary_text = gpt_summarize(self.azure_openai_key, content_text)

            # (5) Insert into DB
            c.execute(
                "INSERT INTO records (date, content) VALUES (?, ?)",
                (pub_date_str, summary_text)
            )
            total_inserted += 1
        conn.commit()
        conn.close()
        print(f"Done. Inserted {total_inserted} articles into DB.")

    def _extract_pub_date_str(self, article) -> str:
        """Extract a YYYY-MM-DD date from the article's pub_date field."""
        pub_date_value = article.get("pub_date")
        if not pub_date_value:
            return ""

        if isinstance(pub_date_value, datetime.datetime):
            return pub_date_value.strftime('%Y-%m-%d')

        if isinstance(pub_date_value, str):
            # Try multiple parse patterns
            for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.datetime.strptime(pub_date_value, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            return pub_date_value[:10]

        return ""

    def _get_article_text(self, article) -> str:
        """
        Combine title, abstract, snippet, lead_paragraph into a single string.
        """
        title = article.get("headline", {}).get("main", "")
        abstract = article.get("abstract", "")
        snippet = article.get("snippet", "")
        lead = article.get("lead_paragraph", "")

        parts = []
        if title.strip():
            parts.append(f"Title: {title}")
        if abstract.strip():
            parts.append(f"Abstract: {abstract}")
        if snippet.strip():
            parts.append(f"Snippet: {snippet}")
        if lead.strip():
            parts.append(f"Lead Paragraph: {lead}")

        return "\n\n".join(parts)


def get_last_date_in_db(db_path: str) -> datetime.datetime:
    """
    Retrieve MAX(date) from 'records' table and parse as datetime.
    If there's no record, default to 2020-01-01
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT MAX(date) FROM records")
    result = c.fetchone()
    conn.close()

    if result and result[0]:
        max_date_str = result[0]  # e.g. '2025-03-10'
        return datetime.datetime.strptime(max_date_str, "%Y-%m-%d")
    else:
        return datetime.datetime(2020, 1, 1)


def job():
    """
    The daily job at 3 AM:
    1. Get the newest date in DB
    2. Use ArticleSearcher to gather articles after that date
    3. Label them with local BERT
    """
    print("[Job] Starting daily job...")

    # (1) Find the latest date
    last_date = get_last_date_in_db(DB_PATH)
    print(f"[Job] Last date in DB is {last_date.strftime('%Y-%m-%d')}")

    # (2) Grab articles after that date
    searcher = ArticleSearcher(
        nyt_api_key=NYT_API_KEY,
        azure_openai_key=AZURE_OPENAI_KEY
    )
    start_dt = last_date + datetime.timedelta(days=1)
    print(f"[Job] Collecting articles after {start_dt} ...")

    searcher.collect_summarized_articles_at_date(start_dt)

    # (3) Label with BERT
    print("[Job] Labeling nuclear attitude...")
    label_nuclear_attitude_bert()

    print("[Job] Done.\n")


def main():
    schedule.every().day.at("00:55").do(job)

    print("Scheduler started. Will run the job every day at 03:00.\n")

    while True:
        schedule.run_pending()
        time.sleep(1)  # e.g. check every 1 second, or 10800 for 3 hours


def clear_database(db_path: str):
    """
    Delete all rows from the 'records' table.
    """
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM records")
    conn.commit()
    conn.close()
    print("All records deleted from the database.")


def first_fetch():
    # clear_database(DB_PATH)
    searcher = ArticleSearcher(
        nyt_api_key=NYT_API_KEY,
        azure_openai_key=AZURE_OPENAI_KEY
    )
    searcher.collect_summarized_articles_after_date(
        datetime.datetime(2021, 3, 31))
    print("[Job] Labeling nuclear attitude...")
    label_nuclear_attitude_bert()

    print("[Job] Done.\n")


def second_fetch():
    # (1) Find the newest date in DB
    last_date = get_last_date_in_db(DB_PATH)
    last_date_str = last_date.strftime('%Y-%m-%d')
    print(f"[second_fetch] Latest date in DB is {last_date_str}")

    # (2) Delete all rows with that date
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE date = ?", (last_date_str,))
    deleted_rows = c.rowcount
    print(
        f"[second_fetch] Deleted {deleted_rows} records for date={last_date_str}")
    conn.commit()
    conn.close()

    # clear_database(DB_PATH)
    searcher = ArticleSearcher(
        nyt_api_key=NYT_API_KEY,
        azure_openai_key=AZURE_OPENAI_KEY
    )
    searcher.collect_summarized_articles_after_date(last_date)
    print("[Job] Labeling nuclear attitude...")
    label_nuclear_attitude_bert()

    print("[Job] Done.\n")


if __name__ == "__main__":
    job()
