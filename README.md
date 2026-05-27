# Sota — Regulatory Requirement Management System
### Rallis-Daw Consulting LLC | Medical Device Compliance Tool

---

## What This Does

Sota helps medical device consultants automatically check whether regulatory requirements
on a device's External Documents List are current or outdated. Upload a PDF, DOCX, or XLSX
file, review the AI-extracted requirements, then run a live compliance check that searches
major regulatory websites for the latest version of each standard.

**Workflow:**
1. Upload your External Documents List (PDF, DOCX, or XLSX)
2. Review and edit the extracted requirements
3. Approve and run the compliance check — results stream in live, row by row
4. Export a formatted Excel report

---

## Prerequisites

- Python 3.8 or higher
- Your own Gemini API key (free — see Step 1)

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

## First-Time Setup

### Step 1 — Get a Gemini API Key

Every teammate needs their own key. Do not share keys.

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key — it starts with `AIza...`
5. Keep it somewhere safe (password manager is ideal)

> You will need a Google account with billing enabled to use the API.
> Your $300 free trial credit covers all normal usage — you will not be charged for testing.

---

### Step 2 — Clone the repo

```bash
git clone <your-repo-url>
cd sota_Parser
```

> **Every command from this point forward must be run from inside the `sota_Parser` folder.**
> If your terminal is not inside the folder, the app will not run correctly.

---

### Step 3 — Create a virtual environment (recommended)

A virtual environment keeps project dependencies isolated from your system Python.

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```
python -m venv .venv
.venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> You'll know it worked when you see `(.venv)` at the start of your terminal prompt.
> Run this activation command every time you open a new terminal for this project.

---

### Step 4 — Install dependencies

With your virtual environment activated:

```bash
pip install -r requirements.txt
```

> On Windows, use `pip` not `pip3`.
> Note: `gunicorn` in requirements.txt is Linux-only (used for Render deployment).
> It will not install on Windows — this is expected and not a problem for local development.

---

### Step 5 — Create your `.env` file

This is where you store your private API key. This file lives only on your machine.

Inside `sota_Parser`, create a new file called exactly `.env` with no other extension.

**On Mac / Linux:**
```bash
touch .env
```

**On Windows:** Open Notepad → File → Save As → navigate to the `sota_Parser` folder →
set "Save as type" to **All Files** → name it `.env` → Save.

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

**This file must never be committed to GitHub.** The `.gitignore` already excludes it.

---

## Step 6 — Verify Your .gitignore Is Set Up

The repo should already include a `.gitignore` file containing:

```
.env
```

To double check, open `.gitignore` and confirm `.env` is listed. If the file doesn't exist,
create it in the `regcheck` folder with just that one line.

This is what prevents your key from ever being pushed to GitHub.

---

## Step 7 — Run the App

With your virtual environment activated:

**On macOS / Linux:**
```bash
python3 app.py
```

**On Windows:**
```
python app.py
```

You should see:

```
==================================================
  Sota  —  Rallis-Daw Consulting
  Regulatory Requirement Management System
==================================================
  OK: Gemini API key loaded

  Open your browser to: http://localhost:5000
  Press Ctrl+C to stop the server
==================================================
```

Open your browser to **http://localhost:5000**

If you see `⚠ WARNING: No API key found!` go back to Step 4.

### If app.run() is commented out, follow the instructions below:

#### Option 1 - Run with Gunicorn

```
python -m gunicorn --bind 0.0.0.0:5000 --timeout 200 src.app:app
```

#### Option 2 - Run with Flask Development Server

**On Windows:**
```
set FLASK_APP=src.app
set FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

**On macOS / Linux:**
```
export FLASK_APP=src.app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```
---

## Every Time You Work On This

1. Open a terminal in the `sota_Parser` folder
2. Activate the virtual environment:
   - Mac/Linux: `source .venv/bin/activate`
   - Windows CMD: `.venv\Scripts\activate`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
3. Run: `python app.py`
4. Open http://localhost:5000
5. When done, press `Ctrl+C` to stop the server

---

## Stopping the App

Press `Ctrl+C` in the terminal.

---

## File Structure

```
sota_Parser/
├── app.py           # Flask routes (pages + API endpoints)
├── parser.py        # Text extraction and Gemini parsing logic
├── checker.py       # Gemini web search per requirement (Google Search grounding)
├── comparator.py    # Date comparison and CURRENT/OUTDATED/UNVERIFIED logic
├── templates/
│   ├── index.html   # Landing page
│   ├── upload.html  # File upload
│   ├── review.html  # Review extracted requirements before running check
│   └── results.html # Live compliance results + Export to Excel
├── static/
│   └── style.css    # All shared CSS
├── .env             # Your API key — NEVER commit this
├── .gitignore       # Excludes .env, __pycache__, venv, etc.
├── requirements.txt # All pip dependencies
├── CLAUDE.md        # Full project context for AI assistants
└── README.md        # This file
```

---

## Troubleshooting

**`No module named X` error**
→ Your virtual environment is not activated, or you didn't run `pip install -r requirements.txt`.
→ Activate the venv and re-run the install command.

**`WARNING: No Gemini API key found`**
→ Check that `.env` exists in the `sota_Parser` folder (not inside a subfolder).
→ Check that it contains `GEMINI_API_KEY=AIza...` with no quotes or spaces.

**`Address already in use` / port 5000 error**
→ Another process is using port 5000. Change `port=5000` to `port=5001` at the bottom
  of `app.py` and go to http://localhost:5001 instead.

**Compliance check returns all Unverified**
→ This is normal on the free Gemini tier for some standards (especially ISO/ASTM/ANSI
  which are behind paywalls). The checker found what it could from public-facing pages.
→ Upgrading to a paid API key does not bypass paywalls, but may improve accuracy.

**`gunicorn` warning in requirements.txt (Windows only)**
→ Expected. gunicorn is Linux-only and used only for Render deployment. Ignore this.

**On Windows, use `python` and `pip` instead of `python3` and `pip3`**

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |

No database credentials needed. All data is in-memory per session — nothing persists
after you close the browser tab or navigate away.

---

## Regulatory Websites Searched

The compliance check searches these 8 sites only:

| Site | Content |
|---|---|
| ecfr.gov | US CFR regulations (21 CFR Part 820, etc.) |
| fda.gov | FDA guidance documents |
| iso.org | ISO standards |
| hhs.gov | US health regulations, HIPAA |
| asq.org | ASQ standards |
| astm.org | ASTM standards |
| ista.org | ISTA packaging standards |
| webstore.ansi.org | ANSI standards |

---

## Status Definitions

| Status | Meaning |
|---|---|
| ✓ Current | Date on file matches or is newer than the current version found online |
| ✗ Outdated | A newer version was found online |
| ⚠ Unverified | Date was blank / `**`, or the standard could not be found online |

---

## Deployment on Render

1. Push the repo to GitHub (`git push`) — make sure `.env` is excluded by `.gitignore`
2. Create a new **Web Service** on Render (render.com)
3. Connect your GitHub repo
4. Set **Build Command** to: `pip install -r requirements.txt`
5. Set **Start Command** to: `gunicorn app:app`
6. Under **Environment Variables**, add `GEMINI_API_KEY` with your key
7. Deploy — free tier spins down after inactivity, which is expected

---

## Notes for Teammates

- **Never commit `.env`** — create your own `.env` locally with your own API key
- **No database** — all data lives in the browser session; nothing persists after closing the tab
- **Each upload starts fresh** — navigating back to `/upload` clears the session
- **The app runs entirely locally** — no cloud calls except to the Gemini API

---

## AI Disclaimer

All results generated by this tool should be independently verified by a qualified
regulatory professional before use in any compliance or regulatory submission.
Rallis-Daw Consulting LLC assumes no liability for the accuracy of AI-generated output.

---

*For internal use only — Rallis-Daw Consulting LLC*