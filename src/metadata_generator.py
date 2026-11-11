import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from src.subtitle_generator import load_audio_waveform

# Common English stopwords to exclude when identifying keywords
STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'in', 'on', 'at',
    'to', 'for', 'with', 'by', 'about', 'like', 'through', 'over', 'before', 'between',
    'after', 'since', 'without', 'under', 'within', 'along', 'following', 'across',
    'behind', 'beyond', 'plus', 'except', 'until', 'around', 'down', 'off', 'above',
    'near', 'there', 'here', 'we', 'you', 'they', 'them', 'this', 'that', 'these',
    'those', 'video', 'every', 'day', 'can', 'could', 'will', 'would', 'shall',
    'should', 'may', 'might', 'must', 'have', 'has', 'had', 'having', 'do', 'does',
    'did', 'doing', 'it', 'its', 'from', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'hey', 'hello', 'there', 'our', 'your', 'their'
}

# Mapping of niche keywords to YouTube Category IDs
CATEGORY_KEYWORDS = {
    "15": ["bee", "bees", "dog", "cat", "pet", "animal", "wildlife", "bird", "fish", "puppy", "kitten", "nature"],
    "28": ["tech", "ai", "technology", "code", "coding", "python", "software", "computer", "hardware", "crypto", "robot"],
    "20": ["game", "gaming", "gameplay", "fps", "playthrough", "minecraft", "roblox", "fortnite", "rpg", "quest"],
    "26": ["how to", "tutorial", "guide", "diy", "recipe", "cook", "cooking", "style", "fashion", "craft", "tips"],
    "27": ["learn", "study", "education", "science", "history", "lesson", "explained", "facts", "knowledge", "school"],
    "23": ["funny", "comedy", "joke", "prank", "hilarious", "laugh", "meme", "humor"],
    "17": ["sport", "sports", "football", "soccer", "basketball", "gym", "workout", "fitness", "training"],
    "19": ["travel", "tour", "hotel", "flight", "trip", "destination", "vacation", "explore"],
    "10": ["music", "song", "beat", "cover", "sing", "rap", "melody", "track"]
}

def clean_topic_from_filename(filename: str) -> str:
    """Extract a clean keyword topic from a video file name."""
    name = os.path.splitext(os.path.basename(filename))[0]

    # Remove generic generator prefixes and random hex hashes (e.g. gemini_generated_video_958eabb5)
    name = re.sub(r'gemini[_\s\-]?generated[_\s\-]?video[_\s\-]?', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b[a-f0-9]{8,12}\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[\-_]', ' ', name)
    name = re.sub(r'\b(1080p|720p|4k|h264|x264|final|render|part\d*|v\d*|clip|vid)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()

    return name.title() if name else "Amazing Video"

def read_accompanying_metadata(video_path: str) -> Optional[Dict[str, Any]]:
    """Check for companion script, description, or notes file alongside the video."""
    base_dir = os.path.dirname(video_path)
    stem = os.path.splitext(os.path.basename(video_path))[0]

    # Check for .json metadata
    json_path = os.path.join(base_dir, f"{stem}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    # Check for .txt or .md companion notes/script
    for ext in [".txt", ".md", ".srt"]:
        text_path = os.path.join(base_dir, f"{stem}{ext}")
        if os.path.exists(text_path):
            try:
                with open(text_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return {"text": content}
            except Exception:
                pass

    return None

def transcribe_video_audio(video_path: str) -> Optional[str]:
    """Transcribe speech in the video using faster-whisper with FFmpeg PCM loading."""
    try:
        audio_np = load_audio_waveform(video_path)
        if audio_np is None or len(audio_np) == 0:
            return None

        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_np, word_timestamps=False)

        spoken_chunks = [s.text.strip() for s in segments if s.text.strip()]
        if spoken_chunks:
            return " ".join(spoken_chunks)
    except Exception as e:
        print(f"[MetadataGenerator] Transcription notice: {e}")
        return None

    return None

def classify_category(text: str) -> str:
    """Classify the most relevant YouTube category ID based on content keywords."""
    text_lower = text.lower()
    scores = {}

    for cat_id, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[cat_id] = score

    if scores:
        return max(scores, key=scores.get)
    return "22"  # Default: People & Blogs

def extract_keywords(text: str, top_n: int = 15) -> List[str]:
    """Extract the most prominent keywords from text, ranked by frequency."""
    raw_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    freq = {}
    for w in raw_words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.keys(), key=lambda w: freq[w], reverse=True)
    return sorted_words[:top_n]

def auto_generate_video_metadata(
    video_path: str,
    progress_callback: Optional[Any] = None,
    force_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Automated end-to-end video analysis:
    1. Inspects video duration & dimensions (Shorts vs Long-form).
    2. Reads companion metadata file if available.
    3. Transcribes speech audio using faster-whisper.
    4. Automatically synthesizes:
       - High-CTR viral Title
       - Structured SEO Description with bullet points and chapters
       - 15-20 Target Tags
       - Top 5-8 Hashtags
       - Suggested Category ID
    """
    if progress_callback:
        progress_callback(0.15, "Inspecting video format & dimensions...")

    # Determine if it's a Short or Long video
    is_short = False
    if force_format == "short":
        is_short = True
    elif force_format == "long":
        is_short = False
    else:
        try:
            from src.youtube_uploader import get_video_info
            info = get_video_info(video_path)
            is_short = info.get("is_short", False)
        except Exception:
            pass

    companion = read_accompanying_metadata(video_path)
    transcript = None
    source = "filename"

    if companion and companion.get("text"):
        transcript = companion["text"]
        source = "companion_file"

    if not transcript:
        if progress_callback:
            progress_callback(0.40, "Listening & transcribing video speech...")
        transcript = transcribe_video_audio(video_path)
        if transcript:
            source = "speech"

    clean_fallback = clean_topic_from_filename(video_path)

    if progress_callback:
        progress_callback(0.75, "Synthesizing SEO title, description & hashtags...")

    if transcript and len(transcript.strip()) > 15:
        # Generate rich metadata from speech transcript
        sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if len(s.strip()) > 8]
        keywords = extract_keywords(transcript, top_n=15)

        # 1. Best Title Selection
        # Prefer questions or strong hook sentences
        hook_candidate = None
        for s in sentences:
            s_clean = s.strip()
            if any(s_clean.lower().startswith(q) for q in ["did you know", "why", "how", "what", "here is", "this is", "never"]):
                hook_candidate = s_clean
                break

        if not hook_candidate and sentences:
            # Pick first complete sentence under 70 chars
            for s in sentences:
                if len(s) <= 70:
                    hook_candidate = s
                    break

        if not hook_candidate:
            hook_candidate = f"{clean_fallback}: Must-Watch!"

        # Capitalize Title cleanly
        title = hook_candidate.rstrip(".!?")
        is_question = any(title.lower().startswith(q) for q in ["did you know", "why", "how", "what", "can you", "is it", "who", "which", "are "])

        if not is_question:
            title = title.title()
        else:
            title = title[0].upper() + title[1:] + "?"

        if is_short:
            if "#Shorts" not in title:
                title = f"{title[:80]} #Shorts"
        else:
            title = re.sub(r'#shorts?\b', '', title, flags=re.IGNORECASE).strip()
            title = title[:95]

        # 2. Category
        category_id = classify_category(transcript)

        # 3. Hashtags
        hashtags = []
        if is_short:
            hashtags.append("#Shorts")
        for kw in keywords[:6]:
            tag = f"#{kw.capitalize()}"
            if tag not in hashtags and tag.lower() != "#shorts":
                hashtags.append(tag)
        if "#Facts" not in hashtags and ("facts" in transcript.lower() or "did you know" in transcript.lower()):
            hashtags.append("#Facts")
        if "#Viral" not in hashtags and len(hashtags) < 7:
            hashtags.append("#Viral")

        # 4. Tags
        tags = []
        if is_short:
            tags.append("shorts")
        for kw in keywords:
            if kw not in tags and kw.lower() != "shorts":
                tags.append(kw)
        if clean_fallback.lower() not in tags:
            tags.insert(0, clean_fallback.lower())
        tags.extend(["viral", "trending", "youtube", "2026"])

        # 5. Formatted Description
        description_lines = [
            f"{transcript.strip()}\n",
            "📌 KEY TAKEAWAYS & HIGHLIGHTS:",
            f"• {sentences[0] if sentences else clean_fallback}",
        ]
        if len(sentences) > 1:
            description_lines.append(f"• {sentences[1]}")
        if len(sentences) > 2:
            description_lines.append(f"• {sentences[2]}")

        description_lines.extend([
            "",
            "🔔 Don't forget to LIKE and SUBSCRIBE for more daily content!",
            "💬 Leave a comment below with your thoughts and feedback.",
            "",
            " ".join(hashtags)
        ])
        description = "\n".join(description_lines)

    else:
        # Fallback to intelligent filename SEO generation
        source = "filename"
        seo = generate_seo_metadata(clean_fallback, video_type="Short" if is_short else "Standard")
        title = seo["recommended_title"]
        description = seo["description"] + "\n\n" + seo["hashtags"]
        tags = seo["tags"]
        hashtags = [h for h in seo["hashtags"].split() if h.startswith("#")]
        category_id = classify_category(clean_fallback)

    return {
        "title": title,
        "description": description,
        "tags": tags[:20],
        "tags_csv": ", ".join(tags[:20]),
        "hashtags": hashtags,
        "hashtags_str": " ".join(hashtags),
        "category_id": category_id,
        "is_short": is_short,
        "transcript": transcript,
        "source": source
    }

def generate_seo_metadata(topic: str, video_type: str = "Standard") -> Dict[str, Any]:
    """
    Generate high-converting titles, formatted SEO descriptions, and tags.
    """
    topic_clean = topic.strip() or "YouTube Video"
    keywords = [w.lower() for w in re.findall(r'\b\w+\b', topic_clean) if len(w) > 2 and w.lower() not in STOPWORDS]

    if video_type == "Short":
        titles = [
            f"The Ultimate {topic_clean} Hack! #Shorts",
            f"Don't Make This {topic_clean} Mistake 😱 #Shorts",
            f"Wait for the end... {topic_clean} #Shorts",
            f"Quick {topic_clean} in 60 Seconds! ⚡ #Shorts",
            f"Why Everyone is Talking About {topic_clean} #Shorts"
        ]
    else:
        titles = [
            f"How to Master {topic_clean} (Step-by-Step Guide)",
            f"The Truth About {topic_clean} in 2026",
            f"{topic_clean} Masterclass: Everything You Need to Know",
            f"I Tried {topic_clean} So You Don't Have To",
            f"Top 5 Secrets for {topic_clean} You Must Know"
        ]

    description = (
        f"In this video, we dive deep into {topic_clean}! Learn everything you need to know "
        f"with clear explanations, practical tips, and actionable takeaways.\n\n"
        f"📌 TIMESTAMPS / CHAPTERS:\n"
        f"0:00 - Introduction to {topic_clean}\n"
        f"1:15 - Key Concepts & Essentials\n"
        f"3:45 - Step-by-Step Walkthrough\n"
        f"6:30 - Common Mistakes to Avoid\n"
        f"8:20 - Summary & Final Tips\n\n"
        f"💡 KEY TAKEAWAYS:\n"
        f"• The foundational principles of {topic_clean}\n"
        f"• How to get results faster and avoid common pitfalls\n"
        f"• Best practices and recommendations for 2026\n\n"
        f"🔔 Don't forget to LIKE, SUBSCRIBE, and ring the bell for more tutorials!\n"
        f"💬 Leave a comment below with your questions or what you want to see next."
    )

    base_tags = [
        topic_clean.lower(),
        f"{topic_clean.lower()} tutorial",
        f"{topic_clean.lower()} guide",
        f"how to {topic_clean.lower()}",
        f"{topic_clean.lower()} 2026",
        "tutorial",
        "guide",
        "tips and tricks",
        "best practices"
    ]
    for kw in keywords:
        if kw not in base_tags:
            base_tags.append(kw)

    hashtags = [f"#{kw.capitalize()}" for kw in keywords[:5]]
    if "#YouTube" not in hashtags:
        hashtags.append("#YouTube")

    return {
        "titles": titles,
        "recommended_title": titles[0],
        "description": description,
        "tags": base_tags[:20],
        "tags_csv": ", ".join(base_tags[:20]),
        "hashtags": " ".join(hashtags)
    }
