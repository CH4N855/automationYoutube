import os
import asyncio
import random
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import config
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

FACT_TEMPLATES = [
    {
        "hook": "Here are 3 mind-blowing facts you didn't know about space!",
        "points": [
            "One day on Venus is actually longer than an entire year on Earth.",
            "There is a giant cloud of alcohol in deep space spanning billions of miles.",
            "If two pieces of the same type of metal touch in space, they bond permanently."
        ],
        "niche": "Space & Science"
    },
    {
        "hook": "Three ancient psychological tricks you need to know today.",
        "points": [
            "If someone is trying to rush you into a decision, wait 10 seconds in silence before answering.",
            "People remember the beginning and the end of any event, but almost always forget the middle.",
            "To build instant trust, mirror the body language and speaking pace of the other person."
        ],
        "niche": "Psychology & Motivation"
    },
    {
        "hook": "Three unbelievable historical facts they didn't teach you in school!",
        "points": [
            "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramids.",
            "In 1325, two Italian cities fought a bloody war over a single wooden bucket.",
            "Napoleon was once attacked and chased by a horde of thousands of bunnies."
        ],
        "niche": "History"
    },
    {
        "hook": "Three game-changing habits for extreme productivity in 2026.",
        "points": [
            "Use the 2-minute rule: if a task takes less than 2 minutes, do it immediately.",
            "Eliminate decision fatigue by planning your top 3 priorities the night before.",
            "Work in 90-minute ultradian rhythm sprints followed by 15-minute phone-free walks."
        ],
        "niche": "Productivity"
    }
]

def select_template_for_niche(niche: Optional[str]) -> Dict[str, Any]:
    """Select appropriate fact template matching the user-selected niche."""
    if not niche or "random" in niche.lower():
        return random.choice(FACT_TEMPLATES)

    words = [w.lower() for w in niche.split() if len(w) > 2]
    matches = [
        t for t in FACT_TEMPLATES
        if any(w in t["niche"].lower() for w in words)
    ]
    if matches:
        return random.choice(matches)
    return random.choice(FACT_TEMPLATES)

async def _synthesize_speech(text: str, output_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_voiceover(text: str, output_path: str, voice: Optional[str] = None) -> str:
    chosen_voice = resolve_voice(voice)
    asyncio.run(_synthesize_speech(text, output_path, chosen_voice))
    return output_path

def create_background_image(width=1080, height=1920, output_path=None) -> str:
    """Create a dark, aesthetic gradient background for Shorts."""
    img = Image.new("RGB", (width, height), color=(15, 15, 22))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(15 + (y / height) * 25)
        g = int(12 + (y / height) * 15)
        b = int(28 + (y / height) * 45)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    if not output_path:
        output_path = str(GENERATED_DIR / "bg.png")
    img.save(output_path)
    return output_path

def create_ai_short(
    topic_or_niche: Optional[str] = None,
    voice: Optional[str] = None,
    custom_script: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Fully automated generation of a 9:16 vertical YouTube Short:
    1. Selects or formats the script matching the requested niche.
    2. Generates realistic AI voiceover with the selected voice via edge-tts.
    3. Assembles video with MoviePy (or FFmpeg fallback) preserving full narration.
    4. Generates an eye-catching matching thumbnail.
    5. Returns video path and metadata ready for upload!
    """
    timestamp = random.randint(1000, 9999)
    video_filename = f"ai_short_{timestamp}.mp4"
    audio_path = str(GENERATED_DIR / f"audio_{timestamp}.mp3")
    video_path = str(GENERATED_DIR / video_filename)

    # 1. Prepare Script matching niche
    if custom_script:
        script_text = custom_script
        title = f"{topic_or_niche or 'Did You Know?'} #Shorts"
    else:
        template = select_template_for_niche(topic_or_niche)
        script_text = f"{template['hook']}. First: {template['points'][0]}. Next: {template['points'][1]}. Finally: {template['points'][2]}. Follow for more daily facts!"
        title = f"{template['hook'].replace('!', '')} 🤯 #Shorts"

    if progress_callback:
        progress_callback(0.15, "Generating AI Voiceover...")

    # 2. Generate Voiceover Audio with selected voice
    generate_voiceover(script_text, audio_path, voice=voice)

    if progress_callback:
        progress_callback(0.40, "Rendering 9:16 Vertical Video...")

    # 3. Create Video - Try MoviePy, fallback to direct FFmpeg to guarantee narration is NEVER lost
    rendered = False
    render_error = None

    try:
        from moviepy import AudioFileClip, ImageClip
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        bg_path = create_background_image()
        bg_clip = ImageClip(bg_path).with_duration(duration)

        final_video = bg_clip.with_audio(audio_clip)
        final_video.write_videofile(
            video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )
        audio_clip.close()
        bg_clip.close()
        final_video.close()
        rendered = True
    except Exception as e:
        render_error = str(e)
        if progress_callback:
            progress_callback(0.60, f"MoviePy notice: muxing with FFmpeg encoder...")

    if not rendered:
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            bg_path = create_background_image()
            cmd = [
                ffmpeg_exe, "-y",
                "-loop", "1",
                "-i", bg_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                video_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            rendered = True
        except Exception as e2:
            raise RuntimeError(f"Video rendering failed (MoviePy: {render_error}; FFmpeg: {e2})")

    if progress_callback:
        progress_callback(0.90, "Creating Thumbnail...")

    from src.thumbnail_generator import generate_youtube_thumbnail
    thumb_path = generate_youtube_thumbnail(title=title, subtitle="VIRAL SHORTS", aspect_ratio="9:16")

    if progress_callback:
        progress_callback(1.0, "Short Generated Successfully!")

    return {
        "video_path": video_path,
        "thumbnail_path": thumb_path,
        "title": title[:100],
        "description": f"{script_text}\n\n🔔 Subscribe for daily mind-blowing shorts!\n#Shorts #Facts #Viral #Learn",
        "tags": ["shorts", "facts", "viral", "didyouknow", "motivation", "daily"],
        "category_id": "27",  # Education
        "is_short": True
    }
