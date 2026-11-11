import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

def has_client_secret() -> bool:
    """Check if client_secret.json exists."""
    return config.CLIENT_SECRET_FILE.exists()

def has_token() -> bool:
    """Check if token.json exists."""
    return config.TOKEN_FILE.exists()

def import_client_secret(source_path: str) -> bool:
    """Import a client_secret.json from any file path on the PC."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "installed" not in data and "web" not in data:
            return False
        with open(config.CLIENT_SECRET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def get_credentials() -> Optional[Credentials]:
    """Retrieve and automatically refresh user credentials."""
    creds = None
    if config.TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), config.YOUTUBE_SCOPES)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(config.TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            creds = None

    return creds

def is_authenticated() -> bool:
    """Check if credentials are currently valid."""
    creds = get_credentials()
    return creds is not None and creds.valid

def authenticate_interactive() -> Tuple[bool, str]:
    """
    Launch interactive OAuth2 flow.
    Opens default browser for user authorization and captures tokens.
    """
    if not has_client_secret():
        return False, "Missing client_secret.json. Please import your Google credentials first."

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(config.CLIENT_SECRET_FILE),
            config.YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message="Opening browser to authorize YouTube Studio Automator...",
            success_message="Authentication successful! You can close this browser tab and return to the Desktop App.",
            open_browser=True
        )
        with open(config.TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        return True, "Successfully connected to YouTube!"
    except Exception as e:
        return False, f"Authentication error: {str(e)}"

def logout() -> bool:
    """Disconnect account by removing token.json."""
    try:
        if config.TOKEN_FILE.exists():
            os.remove(config.TOKEN_FILE)
        return True
    except Exception:
        return False

def get_youtube_service():
    """Build authorized YouTube API service."""
    creds = get_credentials()
    if not creds or not creds.valid:
        return None
    return build("youtube", "v3", credentials=creds)

def get_channel_info() -> Optional[Dict[str, Any]]:
    """Fetch profile data and metrics for the connected YouTube channel."""
    service = get_youtube_service()
    if not service:
        return None

    try:
        response = service.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()

        items = response.get("items", [])
        if not items:
            return None

        channel = items[0]
        snippet = channel.get("snippet", {})
        statistics = channel.get("statistics", {})

        return {
            "id": channel.get("id"),
            "title": snippet.get("title", "Unknown Channel"),
            "custom_url": snippet.get("customUrl", ""),
            "avatar_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
            "subscriber_count": statistics.get("subscriberCount", "Hidden"),
            "video_count": statistics.get("videoCount", "0"),
            "view_count": statistics.get("viewCount", "0")
        }
    except Exception as e:
        return {"error": str(e)}
