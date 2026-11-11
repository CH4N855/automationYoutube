"""Download a single online video to a user-selected folder."""
from pathlib import Path
from urllib.parse import urlparse
import subprocess
import tempfile
import uuid


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
        "no_warnings": True,
    }
    try:
        import imageio_ffmpeg
        options["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    with tempfile.TemporaryDirectory(prefix="studio-download-") as temp:
        options["outtmpl"] = str(Path(temp) / "source.%(ext)s")
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url.strip(), download=True)
            if not info:
                raise RuntimeError("The site did not return video information.")
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
