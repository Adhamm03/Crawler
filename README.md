# Company Info Crawler

Fetches structured company intelligence using Tavily web search + GPT-4o-mini extraction, served via a FastAPI endpoint.

## How It Works

1. Finds the company's official domain via Tavily
2. Crawls up to 10 pages from that domain
3. Extracts structured fields with GPT-4o-mini
4. Falls back to a broad search for any missing fields

Each field gets a confidence score: `high` (from official site) or `low` (from broad search).

## Setup

**1. Install dependencies**
```bash
pip install requests python-dotenv fastapi uvicorn
```

**2. Create `.env`**
```env
TAVILY_KEY=your_tavily_key
OPENAI_KEY=your_openai_key
```

**3. Run**
```bash
uvicorn api:app --reload
```

## API

`POST /company-info`
```json
{ "companyName": "Acme Corp", "country": "United States" }
```

## Output

```json
{
  "company": "Acme Corp",
  "country": "United States",
  "description":         { "value": "...", "score": "high" },
  "employee_count":      { "value": "5000", "score": "high" },
  "locations":           { "value": ["USA", "UK"], "score": "low" },
  "industry":            { "value": "Technology", "score": "high" },
  "key_business_units":  { "value": ["Cloud", "Enterprise"], "score": "high" },
  "source_urls": ["https://acmecorp.com/about"]
}
```

## Project Structure

```
crawler/
├── fetchSite.py     # Crawl + extraction logic
├── api.py           # FastAPI endpoint
└── .env             # API keys (not committed)
```
