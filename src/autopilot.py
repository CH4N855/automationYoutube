import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable

import config
from src.video_generator import create_ai_video, create_ai_short
from src.youtube_uploader import upload_video
from src.storage import add_to_queue
from src.youtube_auth import is_authenticated

class AutoPilotEngine:
    def __init__(self):
        self._recurring_active = False
        self._thread: Optional[threading.Thread] = None
        self._on_status_update: Optional[Callable[[str], None]] = None

    def set_callback(self, cb: Callable[[str], None]):
        self._on_status_update = cb

    def _log(self, msg: str):
        print(f"[AutoPilot] {msg}")
        if self._on_status_update:
            self._on_status_update(msg)

    def generate_and_post_video_now(
        self,
        niche: Optional[str] = None,
        voice: Optional[str] = None,
        format_type: str = "short"
    ) -> Dict[str, Any]:
        """Generate a complete AI video (Short or Long) and upload it directly to YouTube."""
        mode_label = "YouTube Short (9:16)" if str(format_type).lower() == "short" else "YouTube Long Video (16:9)"
        self._log(f"⚡ Starting 100% Automated {mode_label} Generation...")

        try:
            video_data = create_ai_video(topic_or_niche=niche, voice=voice, format_type=format_type)
            self._log(f"🎬 Video created: {video_data['title']}")
        except Exception as e:
            self._log(f"❌ Video generation error: {e}")
            return {"success": False, "error": str(e)}

        if not is_authenticated():
            # If not yet authenticated, safely put in queue
            self._log("⚠️ YouTube not connected. Saving to queue instead.")
            item = add_to_queue(
                video_path=video_data["video_path"],
                title=video_data["title"],
                description=video_data["description"],
                tags=video_data["tags"],
                category_id=video_data["category_id"],
                privacy_status="public",
                thumbnail_path=video_data.get("thumbnail_path"),
                made_for_kids=False
            )
            return {"success": True, "queued": True, "title": video_data["title"]}

        self._log("🚀 Uploading to YouTube...")
        try:
            result = upload_video(
                video_path=video_data["video_path"],
                title=video_data["title"],
                description=video_data["description"],
                tags=video_data["tags"],
                category_id=video_data["category_id"],
                privacy_status="public",
                thumbnail_path=video_data.get("thumbnail_path"),
                made_for_kids=False
            )
            self._log(f"✅ Published successfully! URL: {result['url']}")
            return {"success": True, "url": result["url"], "title": video_data["title"]}
        except Exception as e:
            self._log(f"❌ Upload error: {e}")
            return {"success": False, "error": str(e)}

    def generate_and_post_short_now(self, niche: Optional[str] = None, voice: Optional[str] = None) -> Dict[str, Any]:
        """Backwards compatibility for 9:16 Shorts."""
        return self.generate_and_post_video_now(niche=niche, voice=voice, format_type="short")

    def start_daily_automation(
        self,
        post_hour: int = 18,
        niche: Optional[str] = None,
        voice: Optional[str] = None,
        format_type: str = "short"
    ):
        """Schedule 1 automated video generation and posting every day."""
        if self._recurring_active:
            return
        self._recurring_active = True
        self._thread = threading.Thread(target=self._daily_loop, args=(post_hour, niche, voice, format_type), daemon=True)
        self._thread.start()
        mode_label = "Shorts" if format_type == "short" else "Long Videos"
        self._log(f"🟢 Daily Auto-Pilot activated for {mode_label}. Will post every day at {post_hour:02d}:00.")

    def stop_daily_automation(self):
        self._recurring_active = False
        self._log("🔴 Daily Auto-Pilot stopped.")

    def is_active(self) -> bool:
        return self._recurring_active

    def _daily_loop(self, post_hour: int, niche: Optional[str] = None, voice: Optional[str] = None, format_type: str = "short"):
        last_posted_day = None

        while self._recurring_active:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                # Check if it's the target hour and we haven't posted today
                if now.hour == post_hour and last_posted_day != today_str:
                    self._log(f"⏰ Daily trigger time reached ({now.strftime('%H:%M')}). Generating & Posting...")
                    res = self.generate_and_post_video_now(niche=niche, voice=voice, format_type=format_type)
                    if res.get("success"):
                        last_posted_day = today_str
                    else:
                        self._log(f"⚠️ Daily posting encountered an issue: {res.get('error')}. Will retry next check.")
            except Exception as e:
                self._log(f"⚠️ Exception in daily loop: {e}")

            time.sleep(60)

autopilot = AutoPilotEngine()
