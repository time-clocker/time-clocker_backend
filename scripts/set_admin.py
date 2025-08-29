# scripts/set_admin.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

if not firebase_admin._apps:
    if settings.firebase_credentials_dict:
        cred = credentials.Certificate(settings.firebase_credentials_dict)
    else:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

uid = "p0iwuHgTiefrkOBayhdl2zTPu9x1" 
auth.set_custom_user_claims(uid, {"role": "admin"})
print(f"✅ Rol admin asignado al usuario UID={uid}")
