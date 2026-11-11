import os
import asyncio
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import config
from src.metadata_generator import extract_keywords, classify_category
import edge_tts
from PIL import Image, ImageDraw, ImageFont

GENERATED_DIR = config.DATA_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

VOICES = [
    "en-US-ChristopherNeural",  # Authoritative male
    "en-US-RyanNeural",         # Energetic male
    "en-US-JennyNeural",        # Clear natural female
    "en-GB-SoniaNeural"         # British female
]

VOICE_MAP = {
    "ryan": "en-US-RyanNeural",
    "christopher": "en-US-ChristopherNeural",
    "jenny": "en-US-JennyNeural",
    "sonia": "en-GB-SoniaNeural",
}

def resolve_voice(voice_name: Optional[str]) -> str:
    """Map UI voice dropdown name to Edge-TTS voice identifier."""
    if not voice_name:
        return "en-US-RyanNeural"
    v_lower = voice_name.lower()
    for key, val in VOICE_MAP.items():
        if key in v_lower:
            return val
    if voice_name in VOICES:
        return voice_name
    return "en-US-RyanNeural"

async def _synthesize_speech(text: str, output_path: str, voice: str):
    """Synthesize speech with retry logic and fallback voice if NoAudioReceived occurs."""
    voices_to_try = [voice]
    for fallback in ["en-US-GuyNeural", "en-US-JennyNeural"]:
        if fallback not in voices_to_try:
            voices_to_try.append(fallback)

    last_err = None
    for v in voices_to_try:
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(text, v)
                await communicate.save(output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    return
            except Exception as e:
                last_err = e
                await asyncio.sleep(1.0)

    raise RuntimeError(f"Edge-TTS speech synthesis failed: {last_err}")

def generate_voiceover(text: str, output_path: str, voice: Optional[str] = None) -> str:
    chosen_voice = resolve_voice(voice)
    asyncio.run(_synthesize_speech(text, output_path, chosen_voice))
    return output_path

def create_background_image(width=1080, height=1920, output_path=None) -> str:
    """Create a dark, aesthetic gradient background for Shorts or Long videos."""
    img = Image.new("RGB", (width, height), color=(15, 15, 22))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(15 + (y / height) * 25)
        g = int(12 + (y / height) * 15)
        b = int(28 + (y / height) * 45)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    if not output_path:
        output_path = str(GENERATED_DIR / f"bg_{width}x{height}.png")
    img.save(output_path)
    return output_path

def create_ai_video(
    topic_or_niche: Optional[str] = None,
    voice: Optional[str] = None,
    custom_script: Optional[str] = None,
    format_type: str = "short",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Automated generation of YouTube Short (9:16 vertical) or Long-Form Video (16:9 widescreen):
    1. Uses the required user-supplied narration script.
    2. Generates realistic AI voiceover with the selected voice via edge-tts.
    3. Assembles video with burned captions in 9:16 or 16:9.
    4. Generates an eye-catching matching thumbnail (9:16 or 16:9).
    5. Returns video path and metadata ready for upload!
    """
    is_short = (str(format_type).lower().strip() == "short")
    generation_id = uuid.uuid4().hex
    prefix = "ai_short" if is_short else "ai_long"
    video_filename = f"{prefix}_{generation_id}.mp4"
    audio_path = str(GENERATED_DIR / f"audio_{generation_id}.mp3")
    video_path = str(GENERATED_DIR / video_filename)

    if not custom_script or not custom_script.strip():
        raise ValueError("Provide a script before generating a video.")
    script_text = custom_script.strip()
    title = ((topic_or_niche or "").strip() or script_text.splitlines()[0])[:90]
    desc = script_text
    tags = extract_keywords(script_text)

    if is_short:
        width, height = 1080, 1920
        aspect = "9:16"
        sub_style = "FontName=Arial,FontSize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=300"
        thumb_sub = ""
        title += " #Shorts"
        tags = ["shorts", *tags]
    else:
        width, height = 1920, 1080
        aspect = "16:9"
        sub_style = "FontName=Arial,FontSize=26,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=90"
        thumb_sub = ""

    if progress_callback:
        progress_callback(0.15, "Generating AI Voiceover...")

    generate_voiceover(script_text, audio_path, voice=voice)

    srt_path = None
    if progress_callback:
        progress_callback(0.30, "Generating Animated Subtitles...")
    try:
        from src.subtitle_generator import generate_subtitles_from_audio
        srt_path = generate_subtitles_from_audio(audio_path)
    except Exception as e:
        print(f"Subtitle notice: {e}")

    if progress_callback:
        mode_label = "9:16 Vertical Short" if is_short else "16:9 Widescreen Video"
        progress_callback(0.50, f"Rendering {mode_label}...")

    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        bg_path = create_background_image(
            width=width, height=height,
            output_path=str(GENERATED_DIR / f"bg_{generation_id}.png"),
        )

        cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1",
            "-i", bg_path,
            "-i", audio_path,
        ]

        if srt_path and os.path.exists(srt_path):
            srt_filename = os.path.basename(srt_path)
            cmd.extend(["-vf", f"subtitles={srt_filename}:force_style='{sub_style}'"])

        cmd.extend([
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            video_path
        ])

        run_dir = os.path.dirname(audio_path)
        subprocess.run(cmd, cwd=run_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        raise RuntimeError(f"Video rendering failed: {e}")

    if progress_callback:
        progress_callback(0.90, f"Creating {aspect} Custom Thumbnail...")

    from src.thumbnail_generator import generate_youtube_thumbnail
    thumb_path = generate_youtube_thumbnail(title=title, subtitle=thumb_sub, aspect_ratio=aspect)

    if progress_callback:
        progress_callback(1.0, "Video Generated Successfully!")

    return {
        "video_path": video_path,
        "thumbnail_path": thumb_path,
        "title": title[:100],
        "description": desc,
        "tags": tags,
        "category_id": classify_category(script_text),
        "is_short": is_short
    }

def create_ai_short(
    topic_or_niche: Optional[str] = None,
    voice: Optional[str] = None,
    custom_script: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """Backwards-compatible helper for generating 9:16 Shorts."""
    return create_ai_video(
        topic_or_niche=topic_or_niche,
        voice=voice,
        custom_script=custom_script,
        format_type="short",
        progress_callback=progress_callback
    )
