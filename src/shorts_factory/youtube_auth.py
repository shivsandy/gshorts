from __future__ import annotations
import os
from typing import Any

SCOPES=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly"]

class YouTubeAuthError(RuntimeError): pass

def get_youtube_client() -> Any:
    """Build an authorized API client from GitHub secrets without writing tokens to disk."""
    missing=[k for k in ("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN") if not os.getenv(k)]
    if missing: raise YouTubeAuthError("Missing required GitHub Secrets: "+", ".join(missing))
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc: raise YouTubeAuthError("Google API libraries are missing. Install requirements.txt.") from exc
    try:
        credentials=Credentials(token=None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=SCOPES)
        credentials.refresh(Request())
        return build("youtube","v3",credentials=credentials,cache_discovery=False)
    except Exception as exc:
        raise YouTubeAuthError(f"Google OAuth authorization failed ({type(exc).__name__}). Verify the client, refresh token, consent status, and scopes.") from None
