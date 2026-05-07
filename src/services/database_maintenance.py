from datetime import datetime, timezone
import re

TABLE_NAME     = "extracted_from_List"


def extract_year(date_str):
    if not date_str or date_str.strip().lower() in ("current", "**", ""):
        return None
    match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
    return int(match.group()) if match else None


def enrich_requirement(req, filename):
    date_val = req.get("date", "") or ""
    is_current = date_val.strip().lower() in ("current", "**", "")
    year = extract_year(date_val)
    return {
        "standard_id":         req.get("standard_id", ""),
        "date":                date_val,
        "date_year":           int(year) if year is not None else None,
        "category":            req.get("category", ""),
        "region":              req.get("region", ""),
        "description":         req.get("description", ""),
        "needs_manual_review": is_current,
        "source_filename":     filename,
        "uploaded_at":         datetime.now(timezone.utc).isoformat(),
        "status":              None,
    }


def insert_to_supabase(requirements, supabase_client=None):
    if not supabase_client:
        return 0, "Supabase is not configured."
    try:
        supabase_client.table(TABLE_NAME).insert(requirements).execute()
        return len(requirements), None
    except Exception as e:
        return 0, str(e)