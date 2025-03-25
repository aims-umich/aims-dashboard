import os
import re
import time
import sqlite3
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# Retrieve Azure OpenAI credentials
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION")
AZURE_OPENAI_ORGANIZATION = os.getenv("AZURE_OPENAI_ORGANIZATION")

# Ensure required variables are present
if not all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_VERSION]):
    raise ValueError("Missing Azure OpenAI environment variables!")

# Initialize Azure OpenAI Client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    organization=AZURE_OPENAI_ORGANIZATION
)

# Define database paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(ROOT_DIR, "database", "guardian.db")
extracted_db_path = db_path

def init_extracted_db():
    """Initializes the database to store extracted nuclear content."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Ensure foreign key constraints are enabled
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Ensure `extracted_content` table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extracted_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            extracted_text TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def extract_nuclear_content(text):
    """Uses an AI model to extract nuclear-related content from the given text."""
    try:
        response = client.chat.completions.create(
            model="gpt-35-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "This project is for academic research to analyze nuclear power discussions and help mitigate misinformation.\n"
                        "Extract only single, stand-alone sentences that meet one of the following criteria:\n"
                        "1. The sentence contains the word 'nuclear' or any of its variants. **Every sentence containing 'nuclear' must be extracted with NO exceptions.**\n"
                        "2. The sentence directly discusses nuclear power, nuclear safety, nuclear waste, nuclear policy, or nuclear technology.\n"
                        "\n"
                        "**Strict Extraction Rules:**\n"
                        "- **DO NOT omit any sentence containing 'nuclear'** or its variants, regardless of surrounding context.\n"
                        "- Each extracted sentence must be a complete, stand-alone statement that conveys nuclear-related information.\n"
                        "- Exclude any sentence that only discusses general energy, environmental policy, or economic factors unless they are directly linked to nuclear content.\n"
                        "- **DO NOT return loosely related content** unless they explicitly focus on nuclear topics.\n"
                        "- **DO NOT summarize, paraphrase, modify, or generate new content**—extract sentences exactly as they appear.\n"
                        "- If the article does NOT contain 'nuclear' or any nuclear-related content, return **'None'**.\n"
                        "\n"
                        "**Output Format:**\n"
                        "- Return extracted sentences exactly as they appear in the original document.\n"
                        "- If no nuclear-related content is found, return **'None'**.\n"
                        "- Maintain original punctuation and spacing.\n"
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ],            
            temperature=0
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error processing text: {e}")
        return ""

def extract_nuclear_with_grep(text):
    """Find all sentences containing 'nuclear' using regex (grep equivalent in Python)."""
    nuclear_sentences = re.findall(r'([^.?!]*\bnuclear\b[^.?!]*[.?!])', text, re.IGNORECASE)
    return [sentence.strip() for sentence in nuclear_sentences]

def process_articles():
    """Processes articles from the SQLite database and extracts nuclear-related content."""
    print("Starting nuclear content extraction...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Select only unprocessed articles
    cursor.execute("SELECT id, body_text FROM articles WHERE processed_status IS NULL;")
    articles = cursor.fetchall()
    
    if not articles:
        print("All articles are already processed. No updates needed.")
        conn.close()
        return
    
    conn_extracted = sqlite3.connect(db_path)
    cursor_extracted = conn_extracted.cursor()
    
    for article_id, body_text in articles:
        # Step 1: Extract sentences using GPT
        extracted_content = extract_nuclear_content(body_text)
        gpt_sentences = set(re.split(r'(?<=[.!?])\s+', extracted_content.strip()) if extracted_content and extracted_content != "None" else [])
        
        # Step 2: Use regex (grep alternative) to find all nuclear-related sentences
        grep_sentences = extract_nuclear_with_grep(body_text)
        
        # Step 3: Merge both sources
        all_nuclear_sentences = gpt_sentences.union(grep_sentences)
    
        if all_nuclear_sentences:
            for sentence in all_nuclear_sentences:
                clean_content = sentence.lstrip("-").strip()  # Remove leading hyphen and extra spaces
                if clean_content.lower() != "none":  # Ensure we don't insert "None"
                    cursor_extracted.execute(
                        "INSERT INTO extracted_content (article_id, extracted_text) VALUES (?, ?);",
                        (article_id, clean_content)
                    )
                    conn_extracted.commit()  # Commit after each insert
            print(f"Extracted and saved content for article ID {article_id}")
            cursor.execute("UPDATE articles SET processed_status = 'processed' WHERE id = ?", (article_id,))
        else:
            print(f"No nuclear-related content found in article ID {article_id}")
            cursor.execute("UPDATE articles SET processed_status = 'no_nuclear_content' WHERE id = ?", (article_id,))

        conn.commit()
        time.sleep(0.5)  # Delay to avoid overwhelming API
    
    conn_extracted.close()
    conn.close()
    print("Processing complete.")

if __name__ == "__main__":
    init_extracted_db()
    process_articles()
