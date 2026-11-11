import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

_lock = threading.RLock()

def _read_json(filepath: Path, default: Any) -> Any:
    with _lock:
        if not filepath.exists():
            return default
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

def _write_json(filepath: Path, data: Any) -> None:
    with _lock:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# --- Queue Management ---
def load_queue() -> List[Dict[str, Any]]:
    return _read_json(config.QUEUE_FILE, [])

def save_queue(queue_items: List[Dict[str, Any]]) -> None:
    _write_json(config.QUEUE_FILE, queue_items)

def add_to_queue(
    video_path: str,
    title: str,
    description: str,
    tags: List[str],
    category_id: str,
    privacy_status: str,
    thumbnail_path: Optional[str] = None,
    scheduled_time: Optional[str] = None,
    made_for_kids: bool = False
) -> Dict[str, Any]:
    with _lock:
        queue = load_queue()
        item = {
            "id": str(uuid.uuid4())[:8],
            "video_path": video_path,
            "thumbnail_path": thumbnail_path,
            "title": title,
            "description": description,
            "tags": tags,
            "category_id": category_id,
            "privacy_status": privacy_status,
            "scheduled_time": scheduled_time,
            "made_for_kids": made_for_kids,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled" if scheduled_time else "queued",
            "error_message": None
        }
        queue.append(item)
        save_queue(queue)
        return item

def update_queue_item(item_id: str, updates: Dict[str, Any]) -> bool:
    with _lock:
        queue = load_queue()
        for item in queue:
            if item["id"] == item_id:
                item.update(updates)
                save_queue(queue)
                return True
        return False

def remove_from_queue(item_id: str) -> bool:
    with _lock:
        queue = load_queue()
        new_queue = [item for item in queue if item["id"] != item_id]
        if len(new_queue) != len(queue):
            save_queue(new_queue)
            return True
        return False

# --- History Management ---
def load_history() -> List[Dict[str, Any]]:
    return _read_json(config.HISTORY_FILE, [])

def add_to_history(
    video_id: str,
    title: str,
    privacy_status: str,
    category_id: str,
    thumbnail_url: Optional[str] = None,
    published_at: Optional[str] = None,
    status: str = "success"
) -> Dict[str, Any]:
    with _lock:
        history = load_history()
        item = {
            "id": str(uuid.uuid4())[:8],
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}" if video_id else None,
            "title": title,
            "privacy_status": privacy_status,
            "category_id": category_id,
            "thumbnail_url": thumbnail_url,
            "published_at": published_at or datetime.now().isoformat(),
            "status": status,
            "recorded_at": datetime.now().isoformat()
        }
        history.insert(0, item)
        _write_json(config.HISTORY_FILE, history)
        return item

def clear_history() -> None:
    with _lock:
        _write_json(config.HISTORY_FILE, [])

# --- Settings & Presets Management ---
DEFAULT_SETTINGS = {
    "default_category_id": "22",  # People & Blogs
    "default_privacy": "public",
    "default_tags": ["automation", "youtube"],
    "default_description_footer": "\n\n🔔 Subscribe for more updates!\n👍 Like and share if you found this helpful.",
    "batch_interval_hours": 24,
    "default_made_for_kids": False,
    "watch_folder_enabled": False,
    "watch_folder_path": str(config.WATCH_DIR),
    "auto_scheduler_enabled": True
}

def load_settings() -> Dict[str, Any]:
    current = _read_json(config.SETTINGS_FILE, {})
    return {**DEFAULT_SETTINGS, **current}

def save_settings(settings: Dict[str, Any]) -> None:
    with _lock:
        _write_json(config.SETTINGS_FILE, settings)
