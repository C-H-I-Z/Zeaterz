# Medical Device Regulatory Standards Checker

## What This Does

Local web app that helps medical device consultants check whether the regulatory
standards on a device's External Documents List are current. Upload a PDF, DOCX, or XLSX file and the app uses Gemini AI to extract all the requirements into a structured, categorized table. Results can be downloaded as a JSON file.

---

## ⚠ Important — Read This Before Anything Else

### Your Gemini API Key Is Private

Your Gemini API key is essentially a password that grants access to your Google account's
AI usage and billing. If someone else gets your key they can use it and you will be charged.

**You must never:**
- Paste your API key directly into any code file
- Share your key with teammates, even over private messages
- Commit your `.env` file to GitHub (see below)
- Screenshot your key or post it anywhere

**Everyone on the team gets their own free key.** See Step 1 below.

### What Is a .env File?

A `.env` file is a simple text file that stores secret values like API keys on your local
machine only. It never gets shared or uploaded anywhere. The app reads your key from this
file at startup so you only have to set it once.

Think of it like a personal safe on your laptop — the app knows to look there for the key,
but the file itself never leaves your machine.

### How `.gitignore` Keeps You Safe

The repo includes a `.gitignore` file that tells Git to completely ignore your `.env` file.
This means even if you run `git add .` or `git push`, your `.env` file will never be
uploaded to GitHub. Git will act like it doesn't exist.

**However — you still need to be careful:**
- Never manually add `.env` to a commit
- Never rename your key file to something other than `.env` without updating `.gitignore`
- If you accidentally commit a key, rotate it immediately at https://aistudio.google.com/app/apikey

---

## Prerequisites

- Python 3.8 or higher
- Your own Gemini API key (free — see Step 1)

---

## Step 1 — Get Your Own Gemini API Key

Every teammate needs their own key. Do not share keys.

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key — it starts with `AIza...`
5. Keep it somewhere safe like a password manager or notes app on your phone

> You will need a Google account with billing enabled to use the API.
> Your $300 free trial credit covers all normal usage — you will not be charged for testing.

---

## Step 2 — Clone the Repo and Navigate Into the Folder

```bash
git clone <your-repo-url>
cd Zeaterz
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
