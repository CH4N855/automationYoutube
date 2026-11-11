import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import config
from src.youtube_auth import get_youtube_service
from src.storage import add_to_history

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Inspect video file to detect duration, resolution, size, and YouTube Short eligibility."""
    path = Path(video_path)
    info = {
        "filename": path.name,
        "size_mb": round((path.stat().st_size / (1024 * 1024)), 2) if path.exists() else 0,
        "width": None,
        "height": None,
        "duration_sec": None,
        "is_short": False
    }

    try:
        import cv2
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            info["width"] = width
            info["height"] = height
            info["duration_sec"] = round(duration, 1)
            # YouTube Short criteria: vertical format (height > width) and <= 60.5s duration
            if duration <= 60.5 and height > width:
                info["is_short"] = True
    except Exception:
        pass

    return info

def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    category_id: str = "22",
    privacy_status: str = "public",
    thumbnail_path: Optional[str] = None,
    scheduled_time: Optional[str] = None,
    made_for_kids: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Perform a resumable, chunked upload to YouTube.
    Calls progress_callback(percentage: float (0.0 to 1.0), status_str)
    """
    service = get_youtube_service()
    if not service:
        raise ValueError("YouTube account is not connected. Please authenticate in Settings.")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    status_body: Dict[str, Any] = {
        "selfDeclaredMadeForKids": made_for_kids
    }

    # If scheduled, YouTube requires privacyStatus to be "private"
    if scheduled_time:
        status_body["privacyStatus"] = "private"
        status_body["publishAt"] = scheduled_time
    else:
        status_body["privacyStatus"] = privacy_status

    snippet_body: Dict[str, Any] = {
        "title": title[:100],
        "description": description[:5000],
        "categoryId": category_id
    }
    if tags:
        snippet_body["tags"] = [str(t).strip() for t in tags if str(t).strip()][:50]

    request_body = {
        "snippet": snippet_body,
        "status": status_body
    }

    if progress_callback:
        progress_callback(0.05, "Preparing media chunks...")

    # 4MB chunks for smooth progress updates
    media = MediaFileUpload(
        video_path,
        chunksize=1024 * 1024 * 4,
        resumable=True
    )

    request = service.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                prog = status.progress()  # 0.0 to 1.0
                mapped_progress = 0.05 + (prog * 0.85)
                if progress_callback:
                    progress_callback(mapped_progress, f"Uploading video... {int(prog * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                time.sleep(2)
                continue
            else:
                raise

    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("Upload finished, but no Video ID was returned.")

    if progress_callback:
        progress_callback(0.92, "Setting custom thumbnail...")

    thumbnail_uploaded = False
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            thumb_media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg", resumable=False)
            service.thumbnails().set(
                videoId=video_id,
                media_body=thumb_media
            ).execute()
            thumbnail_uploaded = True
        except Exception as e:
            print(f"Notice: Failed to set custom thumbnail: {e}")

    if progress_callback:
        progress_callback(1.0, "Upload Complete!")

    record = add_to_history(
        video_id=video_id,
        title=title,
        privacy_status=privacy_status,
        category_id=category_id,
        published_at=scheduled_time if scheduled_time else datetime.now().isoformat(),
        status="success"
    )

    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "title": title,
        "thumbnail_uploaded": thumbnail_uploaded,
        "status": "success",
        "record": record
    }
