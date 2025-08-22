import firebase_admin
from firebase_admin import credentials
from app.core.config import settings

def init_firebase():
    if firebase_admin._apps:
        return

    if settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    elif settings.FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(settings.firebase_credentials_dict)
    else:
        raise RuntimeError(
            "Firebase credentials not configured. "
            "Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON in .env"
        )

    firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
