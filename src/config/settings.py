import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# Firebase
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# App Settings
ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx"}