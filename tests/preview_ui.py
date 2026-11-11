"""Offline UI preview: no scheduler, uploads, tray icon, or credential changes.

Run `python tests/preview_ui.py` to review, or add `--check` for layout smoke checks.
"""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
from src.ui import settings_view, queue_view


if __name__ == "__main__":
    examples = [dict(id=str(i), title="Example video with a longer title for checking queue layout",
                     video_path="example.mp4", scheduled_time=None, privacy_status="private",
                     status=status, error_message="Connection failed. Retry when ready." if status == "failed" else None)
                for i, status in enumerate(("queued", "scheduled", "uploading", "failed"))]
    with patch.object(main.scheduler, "start"), \
         patch.object(main.YouTubeAutomatorApp, "_setup_system_tray"), \
         patch.object(main, "is_authenticated", return_value=False), \
         patch.object(settings_view, "is_authenticated", return_value=False), \
         patch.object(main, "load_queue", return_value=[]), \
         patch.object(queue_view, "load_queue", return_value=examples if "--check" in sys.argv else []):
        app = main.YouTubeAutomatorApp()
        app.title("YouTube Automator - Design Preview (offline)")
        app.protocol("WM_DELETE_WINDOW", app.destroy)
        if "--check" in sys.argv:
            try:
                for size in ("1060x700", "1240x860"):
                    app.geometry(size)
                    for key in app.views:
                        app.switch_view(key)
                        app.update()
                        print(f"OK {size}: {key}")
            finally:
                app.destroy()
        else:
            app.mainloop()
