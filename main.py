import os
import json
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SYSTEM_PROMPT = """You are a regulatory document researcher. Your job is to find the most current version and date of any regulatory requirement or guidance document — FDA, ISO, ASTM, ANSI, or any other body.

When given a requirement name and optional description:
1. Figure out which regulatory body owns it based on the name (e.g. "21 CFR" = FDA, "ISO 13485" = ISO, "ASTM F88" = ASTM)
2. Use your search grounding to find the official page for this requirement
3. Find the most recent revision date, issue date, or "last updated" date
4. If it links to a PDF, note the PDF date

Respond ONLY with a valid JSON object, no markdown, no extra text, no code fences. Format:
{
  "title": "official title of the document",
  "source": "regulatory body (e.g. FDA, ISO, ASTM)",
  "latestDate": "the most recent date found (Month YYYY format if possible)",
  "dateSource": "brief note on where this date came from (e.g. PDF header, FDA webpage)",
  "status": "updated or current or unknown",
  "url": "direct URL to the document or official page",
  "notes": "1-2 sentence summary of what was found"
}

Set status to updated if the latest date is newer than the current date provided.
Set status to current if dates match or document is confirmed up to date.
Set status to unknown if you cannot determine.
If you cannot find a specific date, set latestDate to Not found."""


class SearchRequest(BaseModel):
    name: str
    description: str = ""
    currentDate: str = ""


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/api/search")
async def search(req: SearchRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY environment variable not set.")

    user_msg = f"""Find the latest date for this regulatory requirement:
Name: {req.name}
{f"Description: {req.description}" if req.description else ""}
{f"Current date in our document: {req.currentDate}" if req.currentDate else ""}

Search the appropriate regulatory website to find the most current version and its date. Return only a JSON object."""

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_msg}]}
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = e.response.text
            try:
                detail = e.response.json().get("error", {}).get("message", detail)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Gemini API error: {detail}")

    data = resp.json()

    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail=f"Unexpected Gemini response: {str(data)[:300]}")

    clean = raw_text.strip()
    clean = re.sub(r"^```json\s*", "", clean)
    clean = re.sub(r"^```\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean).strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Could not parse JSON from response: {clean[:300]}")

    return parsed
