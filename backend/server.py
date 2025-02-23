import warnings
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --- Step 1: Create FastAPI application and load data ---
app = FastAPI()
train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
train['label'] = train.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})
test['label'] = test.label.replace({'positive': 2, 'negative': 0, 'neutral': 1})

# --- Step 2: Load BERT checkpoint ---
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

# --- Step 3: Function to classify text ---
def classify_text(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        predicted_class = torch.argmax(outputs.logits, dim=1).item()

    return id2label[predicted_class]

# --- Step 4: FastAPI routes ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <html>
    <head><title>Sentiment Classification</title></head>
    <body>
        <h1>Sentiment Classification API</h1>
        <p>Go to <a href='/classify-test/'>Classify Test Data</a> to view results.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/classify-test/", response_class=HTMLResponse)
def classify_test_data():
    results = []

    for _, row in test.iterrows():
        text = row['text']
        true_label = id2label[row['label']]
        predicted_label = classify_text(text)
        results.append((text, true_label, predicted_label))

    html_content = """
    <html>
    <head><title>Classification Results</title></head>
    <body>
        <h1>Sentiment Classification Results</h1>
        <table border='1'>
            <tr>
                <th>Text</th>
                <th>True Label</th>
                <th>Predicted Label</th>
            </tr>
    """

    for text, true_label, predicted_label in results:
        html_content += f"""
        <tr>
            <td>{text}</td>
            <td>{true_label}</td>
            <td>{predicted_label}</td>
        </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

# Run the app with: uvicorn server:app --reload