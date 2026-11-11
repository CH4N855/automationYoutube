"""Scheduler regression checks with in-memory storage and no YouTube calls."""
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.queue = []
        storage = types.ModuleType("src.storage")
        storage.load_queue = lambda: [dict(item) for item in self.queue]

        def update(item_id, updates):
            for item in self.queue:
                if item["id"] == item_id:
                    item.update(updates)
                    return True
            return False

        storage.update_queue_item = update
        storage.remove_from_queue = lambda item_id: self.queue.__setitem__(
            slice(None), [item for item in self.queue if item["id"] != item_id]
        )
        storage.add_to_queue = Mock(side_effect=lambda **kwargs: kwargs)
        uploader = types.ModuleType("src.youtube_uploader")
        uploader.upload_video = Mock(return_value={"video_id": "test"})
        auth = types.ModuleType("src.youtube_auth")
        auth.is_authenticated = lambda: True
        path = Path(__file__).resolve().parents[1] / "src" / "scheduler.py"
        spec = importlib.util.spec_from_file_location("isolated_scheduler", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            "src.storage": storage,
            "src.youtube_uploader": uploader,
            "src.youtube_auth": auth,
        }):
            spec.loader.exec_module(self.module)
        self.scheduler = self.module.SchedulerDaemon()
        self.upload = uploader.upload_video

    def item(self, status="scheduled", scheduled_time="2000-01-01T00:00:00Z"):
        return dict(id="one", video_path="test.mp4", title="Test",
                    description="Test", status=status, scheduled_time=scheduled_time)

    def test_failure_is_not_automatically_retried(self):
        self.queue.append(self.item())
        self.upload.side_effect = RuntimeError("Upload failed")
        self.scheduler._check_queue()
        self.scheduler._check_queue()
        self.assertEqual(self.upload.call_count, 1)
        self.assertEqual(self.queue[0]["status"], "failed")
        self.assertEqual(self.queue[0]["error_message"], "Upload failed")

    def test_failed_item_can_be_manually_retried(self):
        self.queue.append(self.item(status="failed"))
        self.queue[0]["error_message"] = "Previous failure"

        def upload(**kwargs):
            self.assertEqual(self.queue[0]["status"], "uploading")
            self.assertIsNone(self.queue[0]["error_message"])
            return {"video_id": "test"}

        self.upload.side_effect = upload
        self.assertTrue(self.scheduler.process_item("one")["success"])
        self.assertEqual(self.queue, [])

    def test_only_pending_items_are_processed_automatically(self):
        for status in ("failed", "uploading", "completed"):
            with self.subTest(status=status):
                self.queue[:] = [self.item(status=status)]
                self.scheduler._check_queue()
        self.upload.assert_not_called()

    def test_unscheduled_queued_item_uploads(self):
        self.queue.append(self.item(status="queued", scheduled_time=None))
        self.scheduler._check_queue()
        self.upload.assert_called_once()
        self.assertEqual(self.queue, [])

    def test_future_scheduled_item_waits(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        self.queue.append(self.item(scheduled_time=future.isoformat()))
        self.scheduler._check_queue()
        self.upload.assert_not_called()

    def test_batch_converts_offset_to_utc_and_preserves_interval(self):
        start = datetime(2030, 1, 2, 9, tzinfo=timezone(timedelta(hours=7)))
        items = self.scheduler.batch_auto_schedule(
            ["a.mp4", "b.mp4"], "Test", "", [], "22", "public", start, 2
        )
        self.assertEqual([item["scheduled_time"] for item in items],
                         ["2030-01-02T02:00:00Z", "2030-01-02T04:00:00Z"])

    def test_batch_naive_input_remains_utc_as_labeled_in_ui(self):
        items = self.scheduler.batch_auto_schedule(
            ["a.mp4"], "Test", "", [], "22", "public", datetime(2030, 1, 2, 9)
        )
        self.assertEqual(items[0]["scheduled_time"], "2030-01-02T09:00:00Z")


if __name__ == "__main__":
    unittest.main()
