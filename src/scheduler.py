import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Callable

from src.storage import load_queue, update_queue_item, remove_from_queue, add_to_queue
from src.youtube_uploader import upload_video
from src.youtube_auth import is_authenticated

class SchedulerDaemon:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_queue_change: Optional[Callable[[], None]] = None
        self._process_lock = threading.Lock()

    def set_change_callback(self, callback: Callable[[], None]):
        self._on_queue_change = callback

    def start(self, poll_seconds: int = 30):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(poll_seconds,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def is_active(self) -> bool:
        return self._running

    def _loop(self, poll_seconds: int):
        while self._running:
            try:
                self._check_queue()
            except Exception as e:
                print(f"Scheduler loop error: {e}")
            time.sleep(poll_seconds)

    def _check_queue(self):
        if not is_authenticated():
            return

        queue = load_queue()
        now_utc = datetime.now(timezone.utc)

        for item in queue:
            sched_str = item.get("scheduled_time")
            status = item.get("status")

            # Failed uploads require a manual retry; only pending items run automatically.
            if status not in {"queued", "scheduled"}:
                continue

            is_due = False

            # Case A: Scheduled date specified -> compare properly in UTC
            if sched_str:
                try:
                    clean_str = sched_str.replace("Z", "+00:00")
                    sched_dt = datetime.fromisoformat(clean_str)
                    if sched_dt.tzinfo is None:
                        sched_dt = sched_dt.replace(tzinfo=timezone.utc)
                    if now_utc >= sched_dt:
                        is_due = True
                except Exception:
                    pass
            # Case B: Unscheduled item (from folder watcher or instant queue)
            elif status == "queued":
                is_due = True

            if is_due:
                self.process_item(item["id"])
                if self._on_queue_change:
                    self._on_queue_change()

    def process_item(self, item_id: str) -> Dict[str, Any]:
        """Manually or automatically trigger upload for a queued video."""
        with self._process_lock:
            queue = load_queue()
            target = next((item for item in queue if item["id"] == item_id), None)
            if not target:
                return {"success": False, "error": "Item not found"}

            if target.get("status") == "uploading":
                return {"success": False, "error": "Item is already uploading"}

            if not update_queue_item(item_id, {"status": "uploading", "error_message": None}):
                return {"success": False, "error": "Item not found"}

        try:
            result = upload_video(
                video_path=target["video_path"],
                title=target["title"],
                description=target["description"],
                tags=target.get("tags", []),
                category_id=target.get("category_id", "22"),
                privacy_status=target.get("privacy_status", "public"),
                thumbnail_path=target.get("thumbnail_path"),
                scheduled_time=target.get("scheduled_time"),
                made_for_kids=target.get("made_for_kids", False)
            )
            remove_from_queue(item_id)
            return {"success": True, "result": result}
        except Exception as e:
            update_queue_item(item_id, {"status": "failed", "error_message": str(e)})
            return {"success": False, "error": str(e)}

    def batch_auto_schedule(
        self,
        video_paths: List[str],
        base_title: str,
        description: str,
        tags: List[str],
        category_id: str,
        privacy_status: str,
        start_datetime: datetime,
        interval_hours: int = 24,
        made_for_kids: bool = False
    ) -> List[Dict[str, Any]]:
        created = []
        # The UI accepts UTC. Preserve that convention for naive inputs, and
        # convert timezone-aware callers before formatting with the UTC suffix.
        if start_datetime.tzinfo is None:
            current_time = start_datetime.replace(tzinfo=timezone.utc)
        else:
            current_time = start_datetime.astimezone(timezone.utc)

        for index, vpath in enumerate(video_paths):
            title = (f"{base_title} - Part {index + 1}" if len(video_paths) > 1 else base_title) if base_title else os.path.splitext(os.path.basename(vpath))[0]
            iso_time = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            item = add_to_queue(
                video_path=vpath,
                title=title,
                description=description,
                tags=tags,
                category_id=category_id,
                privacy_status=privacy_status,
                scheduled_time=iso_time,
                made_for_kids=made_for_kids
            )
            created.append(item)
            current_time += timedelta(hours=interval_hours)

        if self._on_queue_change:
            self._on_queue_change()

        return created

scheduler = SchedulerDaemon()
