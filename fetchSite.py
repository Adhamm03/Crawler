import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
import json

load_dotenv()

TAVILY_KEY = os.getenv("TAVILY_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")

DATA_FIELDS = ("description", "employee_count", "employee_nationality", "locations", "industry", "years in operation", "Ownership structure", "key_business_units")

FIELD_DESCRIPTIONS = {
    "description":        "A 2-3 sentence summary of what the company does",
    "employee_count":     "Number of employees (exact or approximate)",
    "employee_nationality": "nationalities of employees (display all nationalities you have)",
    "locations":          "Countries or regions where they operate",
    "industry":           "The industry or sector the company operates in",
    "years in operation": "establishment year or how many years this company is in the market",
    "Ownership structure": " shareholders or owners ",
    "key_business_units": "Main divisions, subsidiaries, or business segments",
}


def get_company_info(company_name: str, country: str) -> dict:
    values = {f: None for f in DATA_FIELDS}
    scores = {f: None for f in DATA_FIELDS}
    source_urls = []

    # Phase 1: fetch official site content once, then extract each field independently
    official_text, official_urls = fetch_official_content(company_name, country)
    source_urls.extend(official_urls)

    if official_text:
        for field in DATA_FIELDS:
            val = extract_field_with_llm(official_text, field)
            if val:
                values[field] = val
                scores[field] = "high"

    # Phase 2: for each still-missing field, do its own targeted search + extraction
    for field in DATA_FIELDS:
        if values[field] is None:
            val, urls = fetch_and_extract_field(company_name, country, field)
            source_urls.extend(urls)
            if val:
                values[field] = val
                scores[field] = "low"

    result = {"company": company_name, "country": country}
    for f in DATA_FIELDS:
        result[f] = {"value": values[f], "score": scores[f]}
    result["source_urls"] = list(dict.fromkeys(source_urls))  # deduplicate, preserve order
    return result


def _find_official_domain(company_name: str, country: str) -> str | None:
    """Quick search to discover the company's official domain."""
    res = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": f"{company_name} {country} official website",
            "max_results": 10,
            "include_raw_content": False
        }
    ).json()
    slug = company_name.lower().replace(" ", "")
    for r in res.get("results", []):
        netloc = urlparse(r.get("url", "")).netloc.lower()
        if slug in netloc:
            return netloc.lstrip("www.")
    return None


def fetch_official_content(company_name: str, country: str) -> tuple[str, list[str]]:
    """Fetch raw content from the official site. Returns (combined_text, source_urls)."""
    official_domain = _find_official_domain(company_name, country)

    search_payload = {
        "api_key": TAVILY_KEY,
        "query": f"{company_name} {country} company overview",
        "max_results": 10,
        "include_raw_content": True
    }
    if official_domain:
        search_payload["include_domains"] = [official_domain]

    res = requests.post("https://api.tavily.com/search", json=search_payload).json()
    items = res.get("results", [])
    if not items:
        return "", []

    combined_text = "\n\n".join(
        r.get("raw_content") or r.get("content", "")
        for r in items if r.get("raw_content") or r.get("content")
    )
    urls = [r["url"] for r in items if r.get("url")]
    return combined_text, urls


def fetch_and_extract_field(company_name: str, country: str, field: str) -> tuple:
    """Targeted search + isolated extraction for a single field. Returns (value, source_urls)."""
    query = generate_search_query(company_name, country, field)
    res = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_KEY,
            "query": query,
            "max_results": 5,
            "include_raw_content": True
        }
    ).json()

    items = res.get("results", [])
    if not items:
        return None, []

    urls = [r["url"] for r in items if r.get("url")]
    for r in items:
        text = r.get("raw_content") or r.get("content", "")
        if not text:
            continue
        val = extract_field_with_llm(text, field)
        if val:
            return val, urls
    return None, urls


def generate_search_query(company_name: str, country: str, field: str) -> str:
    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 100,
            "temperature": 0,
            "messages": [{"role": "user", "content":
                f"Write a short web search query to find '{field}' ({FIELD_DESCRIPTIONS.get(field, field)}) for a company called '{company_name}' in {country}. Return ONLY the query string, nothing else."
            }]
        }
    ).json()
    return res["choices"][0]["message"]["content"].strip()


def extract_field_with_llm(page_text: str, field: str):
    """Extract a single specific field from page text. Returns the value or None."""
    field_desc = FIELD_DESCRIPTIONS.get(field, field)
    prompt = f"""From the following company webpage text, extract this specific field:
- {field}: {field_desc}

Respond ONLY as a JSON object with a single key "{field}". Use null if not found.

Content:
{page_text[:15000]}"""

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}"
        },
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 600,
            "temperature": 1,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    raw = res.json()["choices"][0]["message"]["content"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return next((v for k, v in data.items() if k.lower() == field.lower()), None)


# ── Run it ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    info = get_company_info("مدفوعاتكم", "الأردن")
    print(json.dumps(info, indent=2))
