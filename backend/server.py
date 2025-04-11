from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from threads.threads import app as threads_app
from mastodon.mastodon import app as mastodon_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/threads", threads_app)
app.mount("/mastodon", mastodon_app)

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
    <head><title>Combined Sentiment Analysis API</title></head>
    <body>
        <h1>Combined Sentiment Analysis API</h1>
        <p>Available endpoints:</p>
        <ul>
            <li><a href='/threads'>Threads API</a></li>
            <li><a href='/mastodon'>Mastodon API</a></li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Run with: uvicorn server:app --reload