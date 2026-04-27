import json
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

def process_with_ai(text):
    """Process extracted text with Gemini AI."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""
        You are a regulatory document parser for medical devices.

        Extract every standard, regulation, or guidance document from the text below.
        Return ONLY a valid JSON array with no preamble, explanation, or markdown fences.

        Each object must have exactly these fields:
        - "standard_id": the identifier (e.g. "ISO 13485", "21 CFR Part 820", "FDA Guidance 1677")
        - "date": the revision or issue date as written. If marked with ** it means check website for current version — use "Current"
        - "category": the section this belongs to (e.g. "Quality System Management", "Biocompatibility")
        - "region": "US" or "International" based on context
        - "description": a brief description of what this standard covers

        Document text:
        {text}
    """

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Clean up markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        
        if raw.startswith("json"):
            raw = raw[4:]

    raw = raw.strip()

    return json.loads(raw)