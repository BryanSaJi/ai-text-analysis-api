from fastapi import FastAPI
from pydantic import BaseModel
from langdetect import detect
from textblob import TextBlob
from collections import Counter
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

app = FastAPI(
    title="AI Text Analysis API",
    description="Analyzes text for language, sentiment, keywords, and summaries.",
    version="1.2.0"
)

class TextRequest(BaseModel):
    text: str

def extract_keywords(text: str, n: int = 5):
    """Extract most common keywords from text."""
    words = re.findall(r'\b\w+\b', text.lower())
    common_words = Counter(words).most_common(n)
    return [word for word, count in common_words]

def smart_summary(text: str, language: str):
    """Generate a summary that always returns useful content."""
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(language))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, 2)
        summary = " ".join(str(sentence) for sentence in summary_sentences)
        if summary.strip():
            return summary
    except Exception:
        pass

    # Fallback summary if LSA fails
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= 2:
        return text
    elif len(sentences) <= 5:
        return " ".join(sentences[:2])
    else:
        # Keyword-based heuristic fallback
        keywords = extract_keywords(text, 3)
        important_sentences = [
            s for s in sentences if any(k in s.lower() for k in keywords)
        ]
        return " ".join(important_sentences[:2]) or sentences[0]


@app.get("/", include_in_schema=False)
async def health_check():
    """Endpoint to check if the API is running."""
    return {"status": "ok", "service": "Text Analysis API", "version": app.version}


@app.post("/analyze_text")
def analyze_text(request: TextRequest):
    text = request.text.strip()
    if not text:
        return {"error": "Text cannot be empty"}

    # Language detection
    try:
        language = detect(text)
    except:
        language = "unknown"

    # Sentiment analysis
    blob = TextBlob(text)
    sentiment_score = round(blob.sentiment.polarity, 3)
    sentiment_label = (
        "positive" if sentiment_score > 0.1 else
        "negative" if sentiment_score < -0.1 else
        "neutral"
    )

    # Keywords and stats
    keywords = extract_keywords(text)
    word_count = len(text.split())
    character_count = len(text)
    avg_word_length = (
        sum(len(word) for word in text.split()) / word_count
        if word_count else 0
    )

    # Generate reliable summary
    summary = smart_summary(text, language)

    return {
        "language": language,
        "sentiment": sentiment_label,
        "polarity_score": sentiment_score,
        "word_count": word_count,
        "character_count": character_count,
        "keywords": keywords,
        "summary": summary
    }
