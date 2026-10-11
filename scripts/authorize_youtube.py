#!/usr/bin/env python3
"""Run locally to authorize the owner's YouTube channel and obtain a refresh token."""
import argparse
from pathlib import Path

def main() -> int:
    parser=argparse.ArgumentParser(description="Local OAuth consent flow. Never run this in GitHub Actions.")
    parser.add_argument("client_json",help="Path to the downloaded Google OAuth Desktop app client JSON.")
    args=parser.parse_args(); path=Path(args.client_json).expanduser().resolve()
    if not path.is_file(): parser.error("OAuth client JSON file does not exist.")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        parser.error("Install dependencies first: python -m pip install -e .")
    scopes=["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.readonly"]
    flow=InstalledAppFlow.from_client_secrets_file(str(path),scopes=scopes)
    credentials=flow.run_local_server(host="localhost",port=0,open_browser=True,access_type="offline",prompt="consent")
    if not credentials.refresh_token:
        print("No refresh token was returned. Revoke this app in your Google account permissions and repeat consent with offline access.")
        return 2
    print("\nOAuth completed locally. Copy the value below directly into the GitHub Secret YOUTUBE_REFRESH_TOKEN.")
    print("Do not commit it, paste it into issues, or add it to workflow logs.\n")
    print(credentials.refresh_token)
    return 0
if __name__=="__main__": raise SystemExit(main())
