# app/init_firebase.py
import firebase_admin
from firebase_admin import credentials
from app.core.config import settings

def init_firebase():
    if firebase_admin._apps:
        return

    if settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

    elif settings.FIREBASE_CREDENTIALS_JSON:
        creds_dict = settings.firebase_credentials_dict or {}
        if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(creds_dict)

    else:
        raise RuntimeError(
            "Firebase credentials not configured. "
            "Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON"
        )

    firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
