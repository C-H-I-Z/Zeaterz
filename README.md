# Sota — Webscraper (Gemini Version)

Search any regulatory requirement (FDA, ISO, ASTM, ANSI, etc.) and retrieve its latest date.
Powered by Google Gemini 2.0 Flash with Google Search grounding.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Gemini API key**
   - Go to https://aistudio.google.com/app/apikey
   - Create a new API key (free tier available)

3. **Set your API key**
   ```bash
   # Mac/Linux
   export GEMINI_API_KEY=your-key-here

   # Windows (Command Prompt)
   set GEMINI_API_KEY=your-key-here

   # Windows (PowerShell)
   $env:GEMINI_API_KEY="your-key-here"
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --reload
   ```

   ***if that doesnt work try***
   
   ```bash
   python -m uvicorn main:app --reload
   ```


5. **Open in browser**
   ```
   http://localhost:8000
   ```

## How it works

- FastAPI backend receives the requirement name + description
- Calls Gemini 2.0 Flash with Google Search grounding enabled
- Gemini searches the web (FDA, ISO, ASTM, etc.) and returns structured JSON
- Frontend renders the result with a date comparison

## Project Structure

```
sota-fda-checker-gemini/
├── main.py          # FastAPI backend + Gemini API call
├── requirements.txt
├── README.md
└── static/
    └── index.html   # Frontend UI (identical to Claude version)
```

## Next Steps

- Batch check all requirements from an uploaded Excel/CSV
- Export results to XLSX with update flags  
- Add document summarization
- Swap to Claude version once you have an Anthropic API key
