#!/usr/bin/env python3
"""Pixel-based color detection for iPhone back panel photos.

Uses HSV analysis of the center region of the photo (where the phone back
panel typically is) to determine the dominant color independently of the
vision LLM. Helps correct color misdetections in dark/low-contrast photos
where models confuse blue/purple/green/black.

Usage:
    from color_detector import detect_phone_color
    color_name = detect_phone_color(image_path)
"""
import colorsys
import os

# Official-ish Persian color names mapped from hue/saturation analysis
_HUE_COLORS = [
    # (hue_range_low, hue_range_high, persian_name)
    (345, 360, "قرمز"),
    (0, 15, "قرمز"),
    (15, 40, "نارنجی"),
    (40, 65, "طلایی"),
    (65, 90, "زرد"),
    (90, 150, "سبز"),
    (150, 185, "فیروزه‌ای"),
    (185, 235, "آبی"),
    (235, 265, "آبی تیره"),
    (265, 300, "بنفش"),
    (300, 345, "صورتی"),
]

# iPhone Pro model official colors by generation (for reference/correction)
IPHONE_PRO_COLORS = {
    "12": ["آبی", "طلایی", "گرافیت", "نقره‌ای"],
    "13": ["آبی", "طلایی", "گرافیت", "نقره‌ای", "سبز آلپاین"],
    "14": ["بنفش", "طلایی", "مشکی", "نقره‌ای"],
    "15": ["آبی تیتانیوم", "نچرال تیتانیوم", "سفید", "مشکی"],
    "16": ["صحرایی تیتانیوم", "نچرال تیتانیوم", "سفید", "مشکی"],
    "16pro": ["صحرایی تیتانیوم", "نچرال تیتانیوم", "سفید", "مشکی"],
}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _hue_to_color_name(hue, sat, avg_rgb=None):
    """Map hue degrees + saturation + rgb balance to a Persian color name."""
    # Very low saturation => neutral/gray/black (dark phones!)
    if sat < 0.10:
        return "خاکستری"
    if avg_rgb:
        r, g, b = avg_rgb
        # Dark phones (low brightness): value is low -> black/graphite
        brightness = (r + g + b) / 3
        if brightness < 75 and sat < 0.30:
            return "مشکی"
        # Purple detection: red and blue both elevated vs green
        if b > g and r > g and (b - g) > 15 and (r - g) > 10 and b > 60:
            return "بنفش"
        # Green detection: green dominant over red and blue
        if g > r and g > b and (g - r) > 15 and (g - b) > 10:
            return "سبز"
        # Blue detection: blue dominant
        if b > r and b > g and (b - g) > 20:
            return "آبی"
        # Warm: red dominant
        if r > b and r > g and (r - b) > 20:
            return "نارنجی"
    for lo, hi, name in _HUE_COLORS:
        if lo <= hue < hi:
            return name
    return "خاکستری"


def detect_phone_color(image_path, region=(0.25, 0.30, 0.75, 0.70)):
    """Detect dominant color of the phone back panel in a photo.

    Returns (persian_color_name, confidence) where confidence is 0..1.
    Falls back to "نامشخص" on any error.
    """
    try:
        from PIL import Image
    except ImportError:
        return "نامشخص", 0.0

    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        left, top, right, bottom = region
        crop = img.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))

        hues, sats, vals, rgbs = [], [], [], []
        for r, g, b in crop.getdata():
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            hues.append(hh * 360)
            sats.append(ss)
            vals.append(vv)
            rgbs.append((r, g, b))

        # Focus on pixels with meaningful saturation and mid brightness
        # (the phone panel, not background/boxes)
        colored = [(h, s) for h, s, v in zip(hues, sats, vals)
                   if s > 0.12 and 0.12 < v < 0.95]
        if not colored:
            return "خاکستری", 0.3

        avg_hue = sum(h for h, _ in colored) / len(colored)
        avg_sat = sum(s for _, s in colored) / len(colored)
        # average RGB of colored pixels (for channel-balance heuristics)
        colored_rgb = [rgb for rgb, s in zip(rgbs, sats) if s > 0.12]
        avg_rgb = None
        if colored_rgb:
            n = len(colored_rgb)
            avg_rgb = tuple(sum(c[i] for c in colored_rgb) // n for i in range(3))
        # fraction of colored pixels vs total => confidence proxy
        confidence = min(1.0, len(colored) / max(1, len(hues)) * (0.5 + avg_sat))

        return _hue_to_color_name(avg_hue, avg_sat, avg_rgb), confidence
    except Exception:
        return "نامشخص", 0.0


def correct_color_in_post(post_text, detected_color, threshold=0.55):
    """Replace the رنگ: line in a generated post if pixel detection is confident.

    If detected_color is confident and differs from what the LLM wrote,
    prefer the pixel-based color (objective) — but keep the LLM's color if
    detection is low-confidence.
    """
    if not detected_color or detected_color == "نامشخص":
        return post_text

    import re
    # Find the رنگ: line
    match = re.search(r"^رنگ:\s*(.+)$", post_text, re.MULTILINE)
    if not match:
        return post_text

    current = match.group(1).strip()
    # If the LLM already said something very close, don't touch it
    if detected_color in current or current in detected_color:
        return post_text

    return post_text.replace(match.group(0), f"رنگ: {detected_color}")


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        name, conf = detect_phone_color(p)
        print(f"{os.path.basename(p)[:40]:<42} -> {name} (conf={conf:.2f})")
