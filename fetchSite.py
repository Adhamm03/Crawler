import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
import json

load_dotenv()

TAVILY_KEY = os.getenv("TAVILY_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

DATA_FIELDS = ("description", "employee_count", "locations", "industry", "key_business_units")

def get_company_info(company_name: str, country: str) -> dict:
    values = {f: None for f in DATA_FIELDS}
    scores = {f: None for f in DATA_FIELDS}
    source_urls = []

    scraped = fetch(company_name, country)
    source_urls.extend(scraped.pop("source_urls", []))
    for key, val in scraped.items():
        if key in values and val:
            values[key] = val
            scores[key] = "high"

    # Fill remaining nulls with broad search
    null_fields = [f for f in DATA_FIELDS if values[f] is None]
    if null_fields:
        broad_data = fetch_broad(company_name, country, null_fields)
        source_urls.extend(broad_data.pop("source_urls", []))
        for key, val in broad_data.items():
            if key in values and values[key] is None and val:
                values[key] = val
                scores[key] = "low"

    result = {"company": company_name, "country": country}
    for f in DATA_FIELDS:
        result[f] = {"value": values[f], "score": scores[f]}
    result["source_urls"] = source_urls
    return result


def _find_official_domain(company_name: str, country: str) -> str | None:
    """Quick search to discover the company's official domain."""
    res = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": f"{company_name} {country} official website",
            "max_results": 5,
            "include_raw_content": False
        }
    ).json()
    slug = company_name.lower().replace(" ", "")
    for r in res.get("results", []):
        netloc = urlparse(r.get("url", "")).netloc.lower()
        if slug in netloc:
            return netloc.lstrip("www.")
    return None


def fetch(company_name: str, country: str) -> dict:
    official_domain = _find_official_domain(company_name, country)

    search_payload = {
        "api_key": TAVILY_KEY,
        "query": f"{company_name} {country} company overview employees locations offices industry key business units",
        "max_results": 10,
        "include_raw_content": True
    }
    if official_domain:
        search_payload["include_domains"] = [official_domain]

    res = requests.post("https://api.tavily.com/search", json=search_payload).json()

    items = res.get("results", [])
    if not items:
        return {}

    combined_text = "\n\n".join(
        r.get("raw_content") or r.get("content", "")
        for r in items if r.get("raw_content") or r.get("content")
    )

    extracted = extract_with_llm(combined_text)
    extracted["source_urls"] = [r["url"] for r in items if r.get("url")]
    return extracted




def fetch_broad(company_name: str, country: str, missing_fields: list) -> dict:
    """Broad web search (no domain restriction) to fill in missing fields."""
    fields_hint = ", ".join(missing_fields)
    res = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": f"{company_name} {country} {fields_hint}",
            "max_results": 5,
            "include_raw_content": True
        }
    ).json()

    items = res.get("results", [])
    if not items:
        return {}

    combined_text = "\n\n".join(
        r.get("raw_content") or r.get("content", "")
        for r in items if r.get("raw_content") or r.get("content")
    )

    extracted = extract_with_llm(combined_text)
    extracted["source_urls"] = [r["url"] for r in items if r.get("url")]
    return extracted


# ── LLM EXTRACTION (OpenAI) ───────────────────────────────────────────────
def extract_with_llm(page_text: str) -> dict:
    prompt = f"""
From the following company webpage text, extract these fields if present:
- description: A 2-3 sentence summary of what the company does
- employee_count: Number of employees (exact or approximate)
- locations: Countries or regions where they operate
- industry: The industry or sector the company operates in
- key_business_units: Main divisions, subsidiaries, or business segments

Respond ONLY as a JSON object with these exact keys. Use null if not found.

Content (from multiple pages):
{page_text[:15000]}
"""

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}"
        },
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    raw = res.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean)


# ── Run it ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    info = get_company_info("مدفوعاتكم", "الأردن")
    print(json.dumps(info, indent=2))