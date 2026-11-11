import os
import re
from typing import Dict, List, Any, Optional

def clean_topic_from_filename(filename: str) -> str:
    """Extract a clean keyword topic from a video file name."""
    name = os.path.splitext(os.path.basename(filename))[0]
    # Remove common clutter like resolution, dates, underscores
    cleaned = re.sub(r'[\-_]', ' ', name)
    cleaned = re.sub(r'\b(1080p|720p|4k|h264|x264|final|render|part\d*|v\d*)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title() if cleaned else "My Awesome Video"

def generate_seo_metadata(topic: str, video_type: str = "Standard") -> Dict[str, Any]:
    """
    Generate high-converting titles, formatted SEO descriptions, and tags.
    """
    topic_clean = topic.strip() or "YouTube Video"
    keywords = [w.lower() for w in re.findall(r'\b\w+\b', topic_clean) if len(w) > 2]

    # Title variations
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

    # Description structure
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

    # Tags & Hashtags
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

    hashtags = [f"#{kw.capitalize()}" for kw in keywords[:5]] + ["#YouTube", "#Tutorial"]

    return {
        "titles": titles,
        "recommended_title": titles[0],
        "description": description,
        "tags": base_tags[:20],
        "tags_csv": ", ".join(base_tags[:20]),
        "hashtags": " ".join(hashtags)
    }
