## Medical Device Regulatory Standards Checker

---

## What This Does

 local web app that helps medical device consultants check whether the regulatory
standards on a device's External Documents List are current. Upload a PDF, DOCX, or XLSX file
and the app uses Gemini AI to extract all the requirements into a structured, categorized table.
Results can be downloaded as a JSON file.

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

### How .gitignore Keeps You Safe

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
cd regcheck
```

> **Every command from this point forward must be run from inside the `regcheck` folder.**
> If your terminal is not inside the folder, the app will not run correctly.

---

## Step 3 — Install Dependencies

```bash
pip3 install flask google-generativeai pdfplumber python-docx openpyxl python-dotenv
```

On Windows use `pip` instead of `pip3`:
```
pip install flask google-generativeai pdfplumber python-docx openpyxl python-dotenv
```

---

## Step 4 — Create Your .env File

This is where you store your private API key. This file lives only on your machine.

Inside the `regcheck` folder, create a new file called exactly `.env` with no other extension.

**On Mac/Linux:**
```bash
touch .env
```

**On Windows:** Open Notepad, then go to File → Save As, navigate to the `regcheck` folder,
set "Save as type" to "All Files", and name the file `.env`

Open the file and add this one line:

```
GEMINI_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with the key you copied in Step 1.

**Rules for this file:**
- No quotes around the key
- No spaces around the `=`
- No other text or formatting
- Never rename this file
- Never copy this file anywhere else

---

## Step 5 — Verify Your .gitignore Is Set Up

The repo should already include a `.gitignore` file containing:

```
.env
```

To double check, open `.gitignore` and confirm `.env` is listed. If the file doesn't exist,
create it in the `regcheck` folder with just that one line.

This is what prevents your key from ever being pushed to GitHub.

---

## Step 6 — Run the App

```bash
python3 app.py
```

On Windows:
```
python app.py
```

You should see:

```
==================================================
  RegCheck — Requirements Extractor
  Supports: PDF, DOCX, XLSX
==================================================
  ✓ API key loaded from .env

  Open your browser to: http://localhost:5000
  Press Ctrl+C to stop the server
==================================================
```

If you see `⚠ WARNING: No API key found!` go back to Step 4.

---

## Step 7 — Use the App

1. Open your browser and go to **http://localhost:5000**
2. Drag and drop your requirements file onto the drop zone (or click to browse)
3. Supported formats: **PDF**, **DOCX**, **XLSX**
4. Click **"Extract Requirements →"**
5. Wait 15–30 seconds for Gemini to process
6. View the extracted requirements grouped by category
7. Click **"Download JSON"** to save the structured output

---

## Your Folder Should Look Like This

```
regcheck/
├── app.py          ← the app (tracked by git — safe to push)
├── .env            ← your private API key (NOT tracked — never push)
└── .gitignore      ← tells git to ignore .env (tracked by git — safe to push)
```

Only `app.py` and `.gitignore` get pushed to GitHub. The `.env` file stays local forever.

---

## Troubleshooting

**"No API key found" warning on startup**
→ Make sure `.env` exists in the same folder as `app.py`
→ Make sure it contains exactly `GEMINI_API_KEY=your_key_here` with no quotes

**"No module named flask" or similar error**
→ Run the install command from Step 3 again
→ Make sure your terminal is inside the `regcheck` folder

**"Gemini returned an invalid response"**
→ Try again — this is rare and usually fixes itself

**Port 5000 already in use**
→ Change `port=5000` to `port=5001` at the bottom of `app.py`
→ Go to http://localhost:5001 instead

**API key 404 or quota error**
→ Make sure billing is enabled on your Google Cloud account
→ Visit https://aistudio.google.com and confirm your project has billing linked

**On Windows, use `python` and `pip` instead of `python3` and `pip3`**

---

## Stopping the App

Press `Ctrl+C` in the terminal.

---

## AI Disclaimer

This tool uses AI to extract and parse regulatory documents. All results should be
independently verified by a qualified regulatory professional before use in any compliance
or regulatory submission.