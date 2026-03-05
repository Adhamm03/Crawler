# Company Info Crawler

A Python tool that automatically gathers structured company intelligence by combining Tavily web search with OpenAI's GPT-4o-mini for extraction.

## How It Works

1. **Domain discovery** — Searches for the company's official website domain via Tavily.
2. **Targeted crawl** — Fetches up to 10 pages from the official domain, extracting raw content.
3. **LLM extraction** — Sends combined page text to GPT-4o-mini to extract structured fields.
4. **Broad fallback** — If any fields are still missing, performs an unrestricted web search to fill gaps.

### Extracted Fields

| Field | Description |
|---|---|
| `description` | 2–3 sentence company summary |
| `employee_count` | Headcount (exact or approximate) |
| `locations` | Countries/regions of operation |
| `industry` | Sector the company operates in |
| `key_business_units` | Main divisions or subsidiaries |

Each field is returned with a confidence `score`: `"high"` (found on official site) or `"low"` (found via broad search).

---

## Prerequisites

- Python 3.10+
- A [Tavily](https://tavily.com) API key
- An [OpenAI](https://platform.openai.com) API key

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd crawler
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install requests python-dotenv fastapi uvicorn
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
TAVILY_KEY=your_tavily_api_key_here
OPENAI_KEY=your_openai_api_key_here
```

---

## Usage

### Run directly

Edit the `__main__` block at the bottom of `fetchSite.py` to set the company name and country:

```python
if __name__ == "__main__":
    info = get_company_info("Acme Corp", "United States")
    print(json.dumps(info, indent=2))
```

Then run:

```bash
python fetchSite.py
```

### Import as a module

```python
from fetchSite import get_company_info

result = get_company_info("Acme Corp", "United States")
print(result)
```

### Run as an API server

```bash
uvicorn api:app --reload
```

#### `POST /company-info`

```json
{
  "company": "Acme Corp",
  "country": "United States"
}
```

Returns the same JSON structure as the direct usage output below.

#### `GET /health`

Returns `{"status": "ok"}` — use this to verify the server is running.

---

## Output Format

```json
{
  "company": "Acme Corp",
  "country": "United States",
  "description": {
    "value": "Acme Corp is a global provider of...",
    "score": "high"
  },
  "employee_count": {
    "value": "5000",
    "score": "high"
  },
  "locations": {
    "value": ["USA", "UK", "Germany"],
    "score": "low"
  },
  "industry": {
    "value": "Technology",
    "score": "high"
  },
  "key_business_units": {
    "value": ["Cloud Services", "Enterprise Software"],
    "score": "high"
  },
  "source_urls": [
    "https://acmecorp.com/about",
    "https://acmecorp.com/careers"
  ]
}
```

---

## Project Structure

```
crawler/
├── fetchSite.py   # Main crawler and extraction logic
├── api.py         # FastAPI server
├── .env           # API keys (not committed)
└── README.md
```

---

## Notes

- Company name and country can be in any language (Arabic, English, etc.).
- Page text is truncated to 15,000 characters before being sent to the LLM to stay within token limits.
- The tool uses `gpt-4o-mini` by default for cost efficiency.
