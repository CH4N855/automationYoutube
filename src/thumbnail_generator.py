import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

import config

THUMBNAILS_DIR = config.DATA_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

THEME_COLORS = {
    "YouTube Red": {"bg_start": (20, 10, 12), "bg_end": (45, 12, 18), "accent": (255, 0, 0), "badge": (255, 40, 40)},
    "Cyber Neon": {"bg_start": (10, 15, 25), "bg_end": (15, 30, 50), "accent": (0, 240, 255), "badge": (0, 200, 255)},
    "Gold Luxury": {"bg_start": (20, 18, 10), "bg_end": (40, 32, 15), "accent": (255, 195, 0), "badge": (255, 180, 0)},
    "Purple Haze": {"bg_start": (18, 10, 25), "bg_end": (35, 15, 50), "accent": (168, 85, 247), "badge": (147, 51, 234)},
}

def _get_font(size: int):
    """Attempt to load a crisp Windows system font, falling back to default."""
    font_candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def generate_youtube_thumbnail(
    title: str,
    subtitle: Optional[str] = "MUST WATCH",
    theme: str = "YouTube Red",
    aspect_ratio: str = "16:9",
    output_filename: Optional[str] = None
) -> str:
    """
    Generate a high-CTR YouTube thumbnail with bold text, gradient, and glow.
    """
    if aspect_ratio == "9:16":
        width, height = 1080, 1920
        font_size = 90
    else:
        width, height = 1280, 720
        font_size = 72

    color_scheme = THEME_COLORS.get(theme, THEME_COLORS["YouTube Red"])

    # 1. Base Gradient Canvas
    img = Image.new("RGB", (width, height), color=color_scheme["bg_start"])
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(color_scheme["bg_start"][0] * (1 - ratio) + color_scheme["bg_end"][0] * ratio)
        g = int(color_scheme["bg_start"][1] * (1 - ratio) + color_scheme["bg_end"][1] * ratio)
        b = int(color_scheme["bg_start"][2] * (1 - ratio) + color_scheme["bg_end"][2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Glowing Accent Border
    accent = color_scheme["accent"]
    border_thick = 12
    draw.rectangle([border_thick, border_thick, width - border_thick, height - border_thick], outline=accent, width=border_thick)

    # 3. Badge (e.g. "MUST WATCH", "NEW", "2026")
    badge_font = _get_font(int(font_size * 0.45))
    badge_text = f" {subtitle.upper()} " if subtitle else " NEW "
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0]
    badge_h = badge_bbox[3] - badge_bbox[1]

    badge_x = int(width * 0.08)
    badge_y = int(height * 0.15)
    padding = 12
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w + padding * 2, badge_y + badge_h + padding * 2],
        radius=10,
        fill=color_scheme["badge"]
    )
    draw.text((badge_x + padding, badge_y + padding - 4), badge_text, fill=(255, 255, 255), font=badge_font)

    # 4. Main Title - Wrapped into Max 3 Lines with Dropshadow
    title_font = _get_font(font_size)
    words = title.upper().split()
    lines = []
    current_line = []

    max_line_width = int(width * 0.82)
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        if (bbox[2] - bbox[0]) <= max_line_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    lines = lines[:3]  # Keep max 3 lines for clean readability

    # Draw lines
    line_spacing = int(font_size * 1.25)
    start_y = int(badge_y + badge_h + padding * 2 + 35)

    for i, line in enumerate(lines):
        y_pos = start_y + (i * line_spacing)
        x_pos = badge_x

        # Highlight box for first line or key line
        if i == 0 and len(lines) > 1:
            l_bbox = draw.textbbox((0, 0), line, font=title_font)
            lw = l_bbox[2] - l_bbox[0]
            lh = l_bbox[3] - l_bbox[1]
            draw.rounded_rectangle(
                [x_pos - 8, y_pos - 6, x_pos + lw + 16, y_pos + lh + 14],
                radius=8,
                fill=(0, 0, 0, 180)
            )

        # Drop shadow
        draw.text((x_pos + 4, y_pos + 4), line, fill=(0, 0, 0), font=title_font)
        # Main text
        text_color = (255, 255, 255) if i != 1 else accent
        draw.text((x_pos, y_pos), line, fill=text_color, font=title_font)

    # Save Thumbnail
    if not output_filename:
        output_filename = f"thumb_{uuid.uuid4().hex}.jpg"

    output_path = str(THUMBNAILS_DIR / output_filename)
    img.save(output_path, "JPEG", quality=95)
    return output_path
