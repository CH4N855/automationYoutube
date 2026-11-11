"""Reusable script templates for generated videos."""
import random
from typing import Any, Dict, Optional

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

