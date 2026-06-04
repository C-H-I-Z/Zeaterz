"""
checker.py — Per-requirement web search service.

Responsibilities:
  1. Build a targeted Gemini prompt for each requirement (standard ID, description,
     date on file, preferred authoritative site).
  2. Call the Gemini REST API with Google Search grounding enabled so Gemini can
     retrieve live regulatory web pages during generation.
  3. Parse the JSON result from Gemini's response; fall back to regex extraction
     when Gemini wraps the answer in prose instead of pure JSON.
  4. Retry on 429 rate-limit errors (using the delay Gemini specifies) and on
     transient network/server errors (exponential backoff).

Public API:
    check_requirement(req, api_key) -> dict   (single requirement, enriched)
"""

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

# Small stagger so workers don't all fire at the exact same millisecond.
# The ThreadPoolExecutor in app.py controls actual concurrency.
_BASE_DELAY  = 0.5   # seconds to sleep before each request
_MAX_RETRIES = 3     # total attempts per requirement before giving up

# Authoritative sites Gemini is instructed to search.
REGULATORY_SITES = [
    "ecfr.gov", "fda.gov", "iso.org", "hhs.gov",
    "asq.org", "astm.org", "ista.org", "webstore.ansi.org",
]

# Maps standard ID prefixes to their primary authoritative website.
# Matched in order — more-specific prefixes (ISO/IEC) come before shorter ones (ISO).
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

# System-level instruction sent with every Gemini request.
# Sets the persona, explains the task, and defines the exact output format.
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
    """Return the most authoritative website domain for a given standard ID.

    Walks _SITE_MAP in order and returns the first matching domain, or None
    if no prefix matches (caller falls back to searching all sites).
    """
    sid = standard_id.upper()
    for prefix, site in _SITE_MAP:
        if prefix.upper() in sid:
            return site
    return None


def _parse_retry_delay(resp):
    """Read the retryDelay value from a Gemini 429 response body.

    Gemini embeds the recommended wait time in the error details array.
    Adds a 5-second buffer on top of the stated delay to avoid hitting the
    limit again immediately on the next attempt.

    Returns:
        int: seconds to wait before retrying (defaults to 65 if unparseable)
    """
    try:
        for detail in resp.json().get("error", {}).get("details", []):
            delay_str = detail.get("retryDelay", "")
            if delay_str:
                m = re.search(r'\d+', delay_str)
                if m:
                    return int(m.group()) + 5  # add a small buffer
    except Exception:
        pass
    return 65  # safe default when response body is missing or malformed


def _parse_json(raw):
    """Attempt to parse a JSON object from Gemini's raw text response.

    Two strategies are tried in order:
      1. Strip markdown fences and parse the whole string as JSON.
      2. Scan for any {...} substring that contains 'current_version'.

    Returns:
        dict with 'current_version' key, or None if no valid JSON was found.
    """
    # Remove ```json ... ``` fences that Gemini occasionally wraps around output
    raw = re.sub(r"```[a-zA-Z]*\n?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(raw)
        if "current_version" in data:
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: find any {...} block in the response that has the expected key
    for m in re.finditer(r'\{[^{}]+\}', raw, re.DOTALL):
        try:
            data = json.loads(m.group())
            if "current_version" in data:
                return data
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _extract_from_text(raw):
    """Regex fallback when Gemini returns prose instead of JSON.

    Extracts a version string and source URL from free-form text by looking
    for years that appear directly after version/revision/edition keywords.
    Only matches years that are not in the future to avoid hallucinated dates.

    Two special cases handled before regex matching:
      - If the text describes a "continuously maintained" regulation, returns
        current_version="Current" (handled later by comparator.py as CURRENT).
      - If no version is found at all, returns nulls so the caller marks UNVERIFIED.

    Returns:
        dict with 'current_version' and 'source_url' (either may be None).
    """
    # Pull the first HTTP URL from the text to use as source_url
    url_match = re.search(r'https?://[^\s\)\]\"\'<>]+', raw)
    url = url_match.group(0).rstrip('.,)') if url_match else None

    raw_lower = raw.lower()

    # Phrases that signal a CFR-style continuously maintained regulation
    cfr_phrases = ("continuously maintained", "no specific date", "always current",
                   "current version", "current regulation", "no fixed date",
                   "regularly updated", "continuously updated")
    if any(p in raw_lower for p in cfr_phrases):
        return {"current_version": "Current", "source_url": url}

    months = (
        "january|february|march|april|may|june|july|august"
        "|september|october|november|december"
    )
    # Anchor words that signal a version date is nearby
    triggers = r"(?:revised|updated|issued|published|released|version|edition|dated?|effective)"
    recency  = r"(?:latest|current|most recent|newest)"

    # Patterns listed from most-specific (Month YYYY with trigger) to least-specific (year only)
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
            # Reject future years — Gemini occasionally hallucinates upcoming versions
            if year_m and int(year_m.group(1)) <= current_year:
                return {"current_version": matched.title(), "source_url": url}

    return {"current_version": None, "source_url": None}


def check_requirement(req, api_key):
    """Look up the current version of one regulatory requirement via Gemini + Google Search.

    Builds a targeted prompt that tells Gemini which site to search first, then
    calls the Gemini REST API with the google_search tool enabled so Gemini can
    retrieve live pages during generation.

    Retry strategy:
      - 429 rate limit: waits the delay Gemini specifies in the response body.
      - Any other exception: exponential backoff (1 s, 2 s, 4 s).
      - After _MAX_RETRIES failures: returns the requirement unchanged with nulls.

    Special handling for ** items (needs_manual_review=True):
      The prompt explicitly forbids Gemini from returning "Current" and demands
      a specific date, because ** means "no date on file" — not "continuously updated".

    Args:
        req:     Requirement dict (must have 'standard_id', 'description', 'date',
                 'needs_manual_review').
        api_key: Gemini API key string.

    Returns:
        Requirement dict extended with 'current_version', 'source_url', and '_tokens'.
        'current_version' and 'source_url' are None on complete failure.
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
    is_manual    = req.get("needs_manual_review", False)

    # ** items have no baseline date — ask Gemini for the latest version unconditionally.
    # We explicitly ban "Current" here because these items need a real date for comparison.
    if is_manual or date_on_file in ("**", ""):
        date_line = (
            "No specific revision date on file — find the latest published version.\n"
            "Return the actual date (Month YYYY or just the year) this was last "
            "published, issued, or amended. Do NOT return 'Current' as the version — "
            "always provide a specific date, even for continuously maintained regulations.\n"
        )
    else:
        date_line = f"Date currently on file: {date_on_file}\n"

    user_msg = (
        f"Find the CURRENT version and latest revision date for this regulatory document:\n"
        f"Standard: {req['standard_id']}\n"
        + (f"Description: {description}\n" if description else "")
        + date_line
        + f"\n{site_clause}\n\n"
        f'Return ONLY a JSON object: {{"current_version": "Month YYYY", "source_url": "..."}}'
    )

    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        "tools": [{"google_search": {}}],  # enables live web search during generation
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
            # Gemini returns an array of candidates; each has a content with parts.
            # Join all text parts in case the response spans multiple parts.
            parts  = data["candidates"][0]["content"]["parts"]
            raw    = " ".join(p.get("text", "") for p in parts if "text" in p)
            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

            # Try clean JSON parse first; fall back to regex extraction from prose
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
            if attempt < _MAX_RETRIES - 1:
                backoff = 2 ** attempt  # 1s → 2s → 4s
                print(
                    f"[checker] ERROR {req.get('standard_id', '?')} "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES}, retry in {backoff}s): {e}",
                    flush=True,
                )
                time.sleep(backoff)
            else:
                print(
                    f"[checker] FAILED {req.get('standard_id', '?')} "
                    f"after {_MAX_RETRIES} attempts: {e}",
                    flush=True,
                )

    # All retries exhausted — return requirement with nulls so comparator marks UNVERIFIED
    return {**req, "current_version": None, "source_url": None, "_tokens": 0}
