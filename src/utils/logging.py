from flask import request
import firebase_admin
from firebase_admin import firestore

def log_activity(user_id, action, details=None):
    """Log user activity for auditing."""
    try:
        from services.database_maintenance import get_firestore
        db = get_firestore()
        db.collection('activity_logs').add({
            'user_id': user_id or 'anonymous',
            'action': action,
            'details': details or {},
            'ip_address': request.remote_addr if request else None,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Warning: Failed to log activity: {e}")

def log_error(error_message, context=None):
    """Log errors for debugging."""
    try:
        from services.database_maintenance import get_firestore
        db = get_firestore()
        db.collection('error_logs').add({
            'message': error_message,
            'context': context or {},
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Warning: Failed to log error: {e}")