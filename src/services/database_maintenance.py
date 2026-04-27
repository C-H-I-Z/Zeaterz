import json
import firebase_admin
from firebase_admin import credentials
from supabase import create_client
from config.settings import FIREBASE_CREDENTIALS, SUPABASE_URL, SUPABASE_KEY

# Global database clients
firebase_app = None
supabase_client = None

def init_database():
    """Initialize Firebase and Supabase connections."""
    global firebase_app, supabase_client
    
    # Firebase init
    if FIREBASE_CREDENTIALS:
        cert = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cert)
        firebase_app = firebase_admin.initialize_app(cred)
    
    # Supabase init
    if SUPABASE_URL and SUPABASE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return firebase_app, supabase_client

def get_firestore():
    """Get Firestore client."""
    from firebase_admin import firestore
    
    return firestore.client()