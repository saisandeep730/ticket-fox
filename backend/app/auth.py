import hashlib
import json
import logging
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

logger = logging.getLogger("ticket_fox_web.auth")
security = HTTPBearer(auto_error=False)

#: Fixed identity used when no token is presented in mock mode.
MOCK_UID = "demo_user_123"


def _load_credentials():
    """Build Firebase credentials from an inline JSON blob or a key-file path."""
    from firebase_admin import credentials

    raw = (settings.FIREBASE_SERVICE_ACCOUNT_JSON or "").strip().strip('"\'')
    if raw:
        if raw.startswith("{"):
            return credentials.Certificate(json.loads(raw))
        if os.path.exists(raw):
            return credentials.Certificate(raw)
        raise ValueError(
            "FIREBASE_SERVICE_ACCOUNT_JSON must be the service-account JSON itself "
            "or a path to it"
        )

    path = (settings.FIREBASE_CREDENTIALS_PATH or "").strip().strip('"\'')
    if path:
        if os.path.exists(path):
            return credentials.Certificate(path)
        resolved = settings.BACKEND_DIR / path
        if resolved.exists():
            return credentials.Certificate(str(resolved))
    return None



firebase_app = None
try:
    _cred = _load_credentials()
    if _cred is not None:
        import firebase_admin

        firebase_app = firebase_admin.initialize_app(_cred)
        logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize Firebase Admin SDK: {e}")


def _mock_uid(token: str) -> str:
    """A *stable* uid derived from the token.

    ``hash()`` was used before, which is salted per process (PYTHONHASHSEED):
    the same user got a different uid after every restart, so all their saved
    watches "disappeared".
    """
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"mock_{digest}"

async def verify_firebase_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        if settings.ALLOW_MOCK_AUTH:
            return {
                "uid": MOCK_UID,
                "email": "demo@ticketfox.app",
                "name": "Demo User",
                "picture": None,
                "mock": True
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    token = credentials.credentials

    if firebase_app:
        try:
            from firebase_admin import auth
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            detail = f"Invalid Firebase Token: {str(e)}" if settings.DEBUG else "Invalid or expired authorization token"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail
            )
    else:
        if settings.ALLOW_MOCK_AUTH:
            return {
                "uid": _mock_uid(token),
                "email": "user@example.com",
                "name": "Firebase User",
                "mock": True
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase Auth is not configured on server"
        )

async def get_current_user_id(user_data: Dict[str, Any] = Depends(verify_firebase_token)) -> str:
    return user_data.get("uid") or user_data.get("sub") or MOCK_UID


async def get_current_user(user_data: Dict[str, Any] = Depends(verify_firebase_token)) -> Dict[str, Any]:
    """The verified token claims (uid/email/name/picture), used to keep the local
    user profile in sync with the Google account behind the token."""
    uid = user_data.get("uid") or user_data.get("sub") or MOCK_UID
    return {
        "uid": uid,
        "email": user_data.get("email") or "",
        "name": user_data.get("name") or "",
        "picture": user_data.get("picture") or "",
    }

