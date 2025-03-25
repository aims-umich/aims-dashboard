import os
import requests
import sqlite3
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

# Retrieve API keys
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
GUARDIAN_BASE_URL = os.getenv("GUARDIAN_BASE_URL")

# Check if API keys are loaded correctly
if not GUARDIAN_API_KEY or not GUARDIAN_BASE_URL:
    raise ValueError("Missing API keys! Ensure you have a .env file in the guardian directory.")

class GuardianScraper:
    """
    A scraper for fetching articles from The Guardian API and storing them in an SQLite database.

    Attributes:
    - api_key (str): API key for The Guardian API.
    - from_date (str): Start date for fetching articles (YYYY-MM-DD format).
    - to_date (str): End date for fetching articles (YYYY-MM-DD format).
    - db_path (str): Path to the SQLite database.
    - section (str): The Guardian news section to search within.
    - queries (dict): Dictionary of search queries categorized by topic.
    """
    
    def __init__(self, from_date, to_date, db_path):
        """
        Initializes the GuardianScraper with API credentials, date range, and database path.
        Ensures that the database exists and creates the necessary table if not present.
        """
        self.api_key = GUARDIAN_API_KEY
        self.from_date = from_date
        self.to_date = to_date
        self.section = "us-news"
        self.base_url = GUARDIAN_BASE_URL
        self.db_path = db_path
        self.queries = {
            "Nuclear safety": ["risk", "dangerous", "accident", "radiation"],
            "Nuclear economy": ["affordable", "cheap", "expensive", "pricy"],
            "Nuclear technology": ["fusion", "advanced", "future", "SMR"],
            "Nuclear waste": ["radiotoxic", "disposal", "spent-fuel", "contamination"],
            "Nuclear energy": ["green", "carbon-free", "eco-friendly"]
        }

        # Ensure database file exists
        self.init_db()

    def init_db(self):
        """
        Initializes the SQLite database and ensures the directory exists.
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)  # Ensure the directory exists
       
        """
        Initializes the SQLite database and creates the 'articles' table if it does not exist.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                author TEXT,
                section TEXT,
                publish_date TEXT,
                url TEXT UNIQUE,
                word_count INTEGER,
                body_text TEXT,
                processed_status TEXT DEFAULT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def get_total_pages(self, query):
        """
        Fetches the total number of pages of articles that match the query.
        
        Parameters:
        - query (str): Search keyword.
        
        Returns:
        - int: Total number of result pages.
        """
        url = (f"{self.base_url}q={query}&section={self.section}&type=article"
               f"&from-date={self.from_date}&to-date={self.to_date}&order-by=newest"
               f"&page-size=100&page=1&show-fields=bodyText,wordcount,byline&show-tags=all&api-key={self.api_key}")
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['response'].get('pages', 0)
        return 0

    def get_article_data(self, query, page):
        """
        Retrieves article data for a given search query and page number.
        
        Parameters:
        - query (str): Search keyword.
        - page (int): Page number of search results.
        
        Returns:
        - dict or None: JSON response containing article data or None if request fails.
        """
        url = (f"{self.base_url}q={query}&section={self.section}&type=article"
               f"&from-date={self.from_date}&to-date={self.to_date}&order-by=newest"
               f"&page-size=100&page={page}&show-fields=bodyText,wordcount,byline&show-tags=all&api-key={self.api_key}")
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None

    def scrape_articles(self):
        """
        Scrapes articles related to given queries from The Guardian and stores them in the SQLite database.
        Avoids storing duplicate articles based on title.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for keywords in self.queries.values():
            for keyword in keywords:
                search_query = f"Nuclear {keyword}"
                total_pages = self.get_total_pages(search_query)

                for page in range(1, total_pages + 1):
                    json_data = self.get_article_data(search_query, page)

                    if json_data and json_data['response']['status'] == 'ok':
                        results = json_data['response']['results']
                        
                        for result in results:
                            title = result.get("webTitle", "N/A")
                            author = result.get("fields", {}).get("byline", "N/A")
                            publish_date = result.get("webPublicationDate", "N/A")
                            url = result.get("webUrl", "N/A")
                            word_count = result.get("fields", {}).get("wordcount", "N/A")
                            body_text = result.get('fields', {}).get('bodyText', 'No text available')

                            # Avoid storing duplicate articles by checking the title
                            cursor.execute("SELECT id FROM articles WHERE title = ?", (title,))
                            if cursor.fetchone():
                                continue
                            
                            # Insert new article into the database
                            cursor.execute('''
                                INSERT INTO articles (title, author, section, publish_date, url, word_count, body_text)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (title, author, result.get("sectionName", "N/A"), publish_date, url, word_count, body_text))

        conn.commit()
        conn.close()

# Example usage
if __name__ == "__main__":
    from_date = "2024-01-01"
    to_date = "2024-12-31"
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(ROOT_DIR, "database", "guardian.db")# SQLite database path

    scraper = GuardianScraper(from_date, to_date, db_path)
    scraper.scrape_articles()