import os
import time
import json
import threading
from pathlib import Path
from typing import Optional, Callable, Set

import config
from src.storage import add_to_queue, load_settings

PROCESSED_LOG = config.DATA_DIR / "processed_files.json"

class FolderWatcher:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._folder_path: str = str(config.WATCH_DIR)
        self._processed: Set[str] = self._load_processed()
        self._on_video_detected: Optional[Callable[[str], None]] = None

    def set_callback(self, callback: Callable[[str], None]):
        self._on_video_detected = callback

    def _load_processed(self) -> Set[str]:
        if PROCESSED_LOG.exists():
            try:
                with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_processed(self):
        with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
            json.dump(list(self._processed), f, indent=2)

    def start(self, folder_path: Optional[str] = None, interval: int = 5):
        if self._running:
            return
        if folder_path:
            self._folder_path = folder_path

        Path(self._folder_path).mkdir(parents=True, exist_ok=True)
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def is_active(self) -> bool:
        return self._running

    def get_watch_path(self) -> str:
        return self._folder_path

    def _is_file_ready(self, filepath: str) -> bool:
        """Ensure file has finished writing/copying before processing."""
        try:
            size1 = os.path.getsize(filepath)
            time.sleep(1.5)
            size2 = os.path.getsize(filepath)
            return size1 == size2 and size1 > 0
        except Exception:
            return False

    def _watch_loop(self, interval: int):
        valid_extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

        while self._running:
            try:
                if os.path.exists(self._folder_path):
                    for entry in os.scandir(self._folder_path):
                        if entry.is_file():
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in valid_extensions and entry.path not in self._processed:
                                if self._is_file_ready(entry.path):
                                    self._process_new_video(entry.path)
            except Exception as e:
                print(f"Folder watcher error: {e}")

            time.sleep(interval)

    def _process_new_video(self, video_path: str):
        from src.metadata_generator import auto_generate_video_metadata

        settings = load_settings()
        footer = settings.get("default_description_footer", "").strip()

        try:
            # Automatically read and analyze video speech/content for title, description & hashtags
            meta = auto_generate_video_metadata(video_path)
            title = meta.get("title")
            base_desc = meta.get("description", "")
            description = f"{base_desc}\n\n{footer}".strip() if footer else base_desc
            tags = meta.get("tags", settings.get("default_tags", ["automation"]))
            category_id = meta.get("category_id", settings.get("default_category_id", "22"))
        except Exception as e:
            print(f"Metadata auto-generation notice: {e}")
            clean_name = os.path.splitext(os.path.basename(video_path))[0]
            title = clean_name.replace("_", " ").replace("-", " ").title()
            description = f"Auto-uploaded from Watch Folder.\n\n{footer}".strip()
            tags = settings.get("default_tags", ["automation"])
            category_id = settings.get("default_category_id", "22")

        # Automatically check for companion thumbnail or auto-generate a high-CTR thumbnail
        thumb_path = None
        base_no_ext = os.path.splitext(video_path)[0]
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            possible_thumb = base_no_ext + ext
            if os.path.exists(possible_thumb):
                thumb_path = possible_thumb
                break

        if not thumb_path:
            try:
                from src.thumbnail_generator import generate_youtube_thumbnail
                is_short = meta.get("is_short", False) if "meta" in locals() else False
                aspect = "9:16" if is_short else "16:9"
                thumb_path = generate_youtube_thumbnail(
                    title=title,
                    subtitle="SHORTS" if is_short else "MUST WATCH",
                    aspect_ratio=aspect
                )
            except Exception as e:
                print(f"Thumbnail generation notice: {e}")
                thumb_path = None

        item = add_to_queue(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=settings.get("default_privacy", "public"),
            thumbnail_path=thumb_path,
            made_for_kids=settings.get("default_made_for_kids", False)
        )

        self._processed.add(video_path)
        self._save_processed()

        if self._on_video_detected:
            self._on_video_detected(video_path)

        # 1-Click / Zero-Click Auto-Upload immediately if enabled
        if settings.get("watch_folder_auto_upload", True):
            try:
                from src.scheduler import scheduler
                scheduler.process_item(item["id"])
            except Exception as e:
                print(f"Watch folder auto-upload notice: {e}")

folder_watcher = FolderWatcher()
