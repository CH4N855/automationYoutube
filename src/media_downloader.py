"""Download a single online video to a user-selected folder."""
from pathlib import Path
from urllib.parse import urlparse
import subprocess
import tempfile
import uuid
import time


def extract_with_retries(downloader, url, progress=None):
    """Bounded automatic recovery for temporary site/network failures."""
    from yt_dlp.utils import DownloadError
    for attempt in range(3):
        try:
            return downloader.extract_info(url, download=True)
        except DownloadError as exc:
            message = str(exc)
            transient = any(text in message.lower() for text in (
                "403", "429", "timed out", "timeout", "connection", "502", "503",
                "unexpected response"))
            if not transient:
                raise
            if attempt == 2:
                raise RuntimeError(
                    "The website still refused the download after 3 automatic attempts. "
                    "Open the link in your browser to check whether it requires login "
                    "or verification, or is unavailable. No video was saved."
                ) from exc
            delay = 2 ** (attempt + 1)
            if progress:
                progress(None, f"Website request failed. Automatically retrying in {delay}s "
                         f"(attempt {attempt + 2}/3)...")
            time.sleep(delay)


def download_video(url, destination, progress=None):
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a valid http or https video link.")
    folder = Path(destination).expanduser()
    if not folder.is_dir():
        raise ValueError("Choose an existing download folder.")

    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies with: python -m pip install -r requirements.txt") from exc

    def hook(event):
        if not progress:
            return
        if event.get("status") == "downloading":
            total = event.get("total_bytes") or event.get("total_bytes_estimate")
            amount = event.get("downloaded_bytes", 0)
            progress(min(amount / total, 1.0) if total else None, "Downloading video...")
        elif event.get("status") == "finished":
            progress(None, "Download finished. Processing video...")

    options = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "windowsfilenames": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_color": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "no_warnings": True,
    }
    if parsed.hostname == "tiktok.com" or (parsed.hostname or "").endswith(".tiktok.com"):
        options["http_headers"] = {"Referer": "https://www.tiktok.com/"}
    try:
        import imageio_ffmpeg
        options["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    with tempfile.TemporaryDirectory(prefix="studio-download-") as temp:
        options["outtmpl"] = str(Path(temp) / "source.%(ext)s")
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                info = extract_with_retries(downloader, url.strip(), progress)
                if not info:
                    raise RuntimeError("The site did not return video information.")
        except (yt_dlp.utils.DownloadError, RuntimeError):
            if not (parsed.hostname == 'tiktok.com' or (parsed.hostname or '').endswith('.tiktok.com')):
                raise
            from src.browser_downloader import browser_download
            # Clear incomplete downloads only inside our private temporary directory.
            for partial in Path(temp).glob('source.*'):
                partial.unlink()
            browser_download(url.strip(), Path(temp) / 'source.mp4', progress)
        sources = [p for p in Path(temp).glob("source.*") if p.suffix.lower() not in (".part", ".ytdl")]
        if len(sources) != 1:
            raise RuntimeError("Could not locate the downloaded video for processing.")
        if progress:
            progress(None, "Cropping, enhancing color, and adjusting speed...")
        import imageio_ffmpeg
        output = Path(temp) / "processed.mp4"
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(sources[0]),
               "-vf", "crop=trunc(iw*0.9/2)*2:trunc(ih*0.9/2)*2,eq=saturation=1.2:contrast=1.05,setpts=PTS/1.2",
               "-af", "atempo=1.2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-movflags", "+faststart", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        if result.returncode:
            raise RuntimeError("Video processing failed: " + result.stderr[-1200:])
        # Copy into a non-video temporary name, then rename once complete so the watcher
        # cannot pick up an incomplete file, including across filesystem volumes.
        final = folder / f"video_{uuid.uuid4().hex[:12]}.mp4"
        staged = folder / (final.name + ".part")
        try:
            import shutil
            shutil.copyfile(output, staged)
            staged.replace(final)
        finally:
            staged.unlink(missing_ok=True)
        return final.name
