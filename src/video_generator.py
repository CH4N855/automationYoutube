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

    # 2.5 Generate Animated Subtitles with Whisper
    srt_path = None
    if progress_callback:
        progress_callback(0.30, "Generating Animated Subtitles...")
    try:
        from src.subtitle_generator import generate_subtitles_from_audio
        srt_path = generate_subtitles_from_audio(audio_path)
    except Exception as e:
        print(f"Subtitle notice: {e}")

    if progress_callback:
        progress_callback(0.50, "Rendering 9:16 Vertical Video...")

    # 3. Create Video with direct FFmpeg stream muxing & burned subtitles
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        bg_path = create_background_image()

        cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1",
            "-i", bg_path,
            "-i", audio_path,
        ]

        if srt_path and os.path.exists(srt_path):
            srt_filename = os.path.basename(srt_path)
            sub_filter = f"subtitles={srt_filename}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=300'"
            cmd.extend(["-vf", sub_filter])

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
