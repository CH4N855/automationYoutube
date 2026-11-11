import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
CREDENTIALS_DIR = DATA_DIR / "credentials"
WATCH_DIR = BASE_DIR / "watch_folder"

for folder in [DATA_DIR, UPLOADS_DIR, THUMBNAILS_DIR, CREDENTIALS_DIR, WATCH_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# File Paths
QUEUE_FILE = DATA_DIR / "queue.json"
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"

# YouTube OAuth Scopes
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

# YouTube Categories
YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
}

CATEGORY_NAME_TO_ID = {name: cid for cid, name in YOUTUBE_CATEGORIES.items()}
