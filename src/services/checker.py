import datetime
import json
import re
import time
import httpx


GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Free tier: ~10 RPM. Each request takes ~3-5 s, so a 2 s base delay keeps
# us comfortably under the limit without adding much total runtime.
_BASE_DELAY  = 2
_MAX_RETRIES = 3

REGULATORY_SITES = [
    "ecfr.gov", "fda.gov", "iso.org", "hhs.gov",
    "asq.org", "astm.org", "ista.org", "webstore.ansi.org",
]

_SITE_MAP = [
    ("21 CFR",    "ecfr.gov"),
    ("CFR",       "ecfr.gov"),
    ("HIPAA",     "hhs.gov"),
    ("HHS",       "hhs.gov"),
    ("FDA",       "fda.gov"),
    ("ISO/TR",    "iso.org"),
    ("ISO/IEC",   "iso.org"),
    ("EN ISO",    "iso.org"),
    ("EN 6",      "iso.org"),
    ("ISO",       "iso.org"),
    ("ASTM",      "astm.org"),
    ("ANSI",      "webstore.ansi.org"),
    ("ISTA",      "ista.org"),
    ("ASQ",       "asq.org"),
]

_SYSTEM_PROMPT = """You are a regulatory document researcher specializing in medical device \
                    standards and FDA guidance documents. Your job is to find the most current version and date \
                    of any regulatory requirement or guidance document.
                    When given a document name and description:
                    1. Identify the regulatory body ("21 CFR" = FDA/eCFR, "ISO" = iso.org, "FDA Guidance XXXXX" = search fda.gov for that guidance number/title, "ASTM" = astm.org)
                    2. Use Google Search to find the official page for this exact document
                    3. Find the most recent revision date, issue date, or version number
                    4. For FDA Guidance documents: search fda.gov using both the guidance ID number AND the description/title to locate the correct document
                    Respond ONLY with a valid JSON object — no markdown, no code fences, no extra text:
                    {"current_version": "...", "source_url": "..."}
                    Rules:
                    - current_version: the latest revision date in "Month YYYY" format when possible (e.g. "March 2025", "April 2022"). Use year only if month is unavailable (e.g. "2023").
                    - For US CFR regulations on ecfr.gov that are continuously maintained with no fixed issue date: use "Current".
                    - source_url: the exact URL where you found this information.
                    - If the document cannot be found: {"current_version": null, "source_url": null}"""


def _primary_site(standard_id):
    sid = standard_id.upper()

    for prefix, site in _SITE_MAP:
        if prefix.upper() in sid:
            return site
        
    return None


def _parse_retry_delay(resp):
    """Read retryDelay from a 429 response body; default to 65 s."""

    try:
        for detail in resp.json().get("error", {}).get("details", []):
            delay_str = detail.get("retryDelay", "")
            if delay_str:
                m = re.search(r'\d+', delay_str)
                if m:
                    return int(m.group()) + 5  # add a small buffer
                
    except Exception:
        pass
    
    return 65


def _parse_json(raw):
    raw = re.sub(r"```[a-zA-Z]*\n?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(raw)
        if "current_version" in data:
            return data
        
    except (json.JSONDecodeError, ValueError):
        pass
    
    for m in re.finditer(r'\{[^{}]+\}', raw, re.DOTALL):
        try:
            data = json.loads(m.group())
            if "current_version" in data:
                return data
            
        except (json.JSONDecodeError, ValueError):
            continue
        
    return None


def _extract_from_text(raw):
    """Context-aware fallback: only extract years that follow version keywords."""

    url_match = re.search(r'https?://[^\s\)\]\"\'<>]+', raw)
    url = url_match.group(0).rstrip('.,)') if url_match else None

    raw_lower = raw.lower()

    cfr_phrases = ("continuously maintained", "no specific date", "always current",
                   "current version", "current regulation", "no fixed date",
                   "regularly updated", "continuously updated")
    
    if any(p in raw_lower for p in cfr_phrases):
        return {"current_version": "Current", "source_url": url}

    months = (
        "january|february|march|april|may|june|july|august"
        "|september|october|november|december"
    )

    triggers = r"(?:revised|updated|issued|published|released|version|edition|dated?|effective)"
    recency  = r"(?:latest|current|most recent|newest)"

    patterns = [
        rf"{triggers}[^.{{}}]{{0,30}}((?:{months})\s+(?:19|20)\d{{2}})",
        rf"{triggers}[^.{{}}]{{0,20}}((?:19|20)\d{{2}})",
        rf"{recency}[^.{{}}]{{0,40}}((?:{months})\s+(?:19|20)\d{{2}})",
        rf"{recency}[^.{{}}]{{0,30}}((?:19|20)\d{{2}})",
    ]

    current_year = datetime.date.today().year
    
    for pattern in patterns:
        m = re.search(pattern, raw_lower)
        if m:
            matched = m.group(1).strip()
            year_m = re.search(r'((?:19|20)\d{2})', matched)
            if year_m and int(year_m.group(1)) <= current_year:
                return {"current_version": matched.title(), "source_url": url}

    return {"current_version": None, "source_url": None}


def check_requirement(req, api_key):
    """Check one requirement via Gemini REST API with Google Search grounding.
    Throttles requests and retries automatically on 429 rate-limit errors.
    """

    time.sleep(_BASE_DELAY)  # stay under the free-tier RPM cap

    primary     = _primary_site(req["standard_id"])
    all_sites   = ", ".join(REGULATORY_SITES)

    site_clause = (
        f"Search primarily on {primary} (also check: {all_sites} if needed)."
        if primary
        else f"Search these sites: {all_sites}."
    )

    description  = (req.get("description") or "").strip()
    date_on_file = (req.get("date") or "").strip()

    user_msg = (
        f"Find the CURRENT version and latest revision date for this regulatory document:\n"
        f"Standard: {req['standard_id']}\n"
        + (f"Description: {description}\n" if description else "")
        + (f"Date currently on file: {date_on_file}\n" if date_on_file else "")
        + f"\n{site_clause}\n\n"
        f'Return ONLY a JSON object: {{"current_version": "Month YYYY", "source_url": "..."}}'
    )

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }

    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(f"{GEMINI_URL}?key={api_key}", json=payload)

            if resp.status_code == 429:
                delay = _parse_retry_delay(resp)
                print(
                    f"[checker] Rate limited ({req['standard_id']}), "
                    f"retry {attempt + 1}/{_MAX_RETRIES} in {delay}s…",
                    flush=True,
                )
                time.sleep(delay)
                continue

            resp.raise_for_status()

            data   = resp.json()
            parts  = data["candidates"][0]["content"]["parts"]
            raw    = " ".join(p.get("text", "") for p in parts if "text" in p)
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

            result = _parse_json(raw)
            
            if result is None or result.get("current_version") is None:
                result = _extract_from_text(raw)

            print(
                f"[checker] {req['standard_id']} → "
                f"{result.get('current_version')} | "
                f"{result.get('source_url') or 'no url'}",
                flush=True,
            )

            return {
                **req,
                "current_version": result.get("current_version"),
                "source_url":      result.get("source_url"),
                "_tokens":         tokens,
            }

        except Exception as e:
            print(f"[checker] ERROR {req.get('standard_id', '?')}: {e}", flush=True)
            break

    return {**req, "current_version": None, "source_url": None, "_tokens": 0}