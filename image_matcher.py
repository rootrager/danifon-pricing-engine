"""
Image Matcher: picks the best product photo from iphone/ folder
based on the generated post text (model + color extraction).
"""
import os
import re
import random

IPHONE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iphone")

# ─── Color name mapping (Persian/English/Finglish → filename keywords) ───
COLOR_MAP = {
    # Black
    "مشکی": ["black", "meshki"],
    "مشكى": ["black", "meshki"],
    "black": ["black", "meshki"],
    "meshki": ["meshki", "black"],
    # White
    "سفید": ["white", "sefid"],
    "سفيد": ["white", "sefid"],
    "white": ["white", "sefid"],
    "sefid": ["sefid", "white"],
    # Blue
    "آبی": ["blue", "abi"],
    "ابی": ["blue", "abi"],
    "blue": ["blue", "abi"],
    "abi": ["abi", "blue"],
    # Green
    "سبز": ["green", "sabz"],
    "green": ["green", "sabz"],
    "sabz": ["sabz", "green"],
    # Gold
    "طلایی": ["gold"],
    "gold": ["gold"],
    # Purple / Violet
    "بنفش": ["banafsh"],
    "purple": ["banafsh"],
    "بنفشه": ["banafsh"],
    "banafsh": ["banafsh"],
    # Pink
    "صورتی": ["pinky", "pink"],
    "pink": ["pinky", "pink"],
    "pinky": ["pinky", "pink"],
    # Natural / Titanium Natural
    "نچرال": ["nachral", "natural"],
    "natural": ["nachral", "natural"],
    "natural titanium": ["nachral"],
    "تیتانیوم": ["nachral", "natural"],
    # Desert
    "دزرت": ["desert"],
    "desert": ["desert"],
    "desert titanium": ["desert"],
    # Orange
    "نارنجی": ["orange", "ornage"],
    "orange": ["orange", "ornage"],
}

# ─── Model name normalization ───
# Maps various ways LLM might write model names → filename prefix
MODEL_PATTERNS = [
    # Order matters: more specific first
    (r"(?:iphone\s*)?17\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "17max"),
    (r"(?:iphone\s*)?17\s*(?:pro|پرو)", "17pro"),
    (r"\b17\b(?!\s*میلیون|\s*م\b)", "17normal"),

    (r"(?:iphone\s*)?16\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "16max"),
    (r"(?:iphone\s*)?16\s*(?:pro|پرو)", "16pro"),
    (r"\b16\b(?!\s*میلیون|\s*م\b)", "16normal"),

    (r"(?:iphone\s*)?15\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "15max"),
    (r"(?:iphone\s*)?15\s*(?:pro|پرو)", "15pro"),
    (r"\b15\b(?!\s*میلیون|\s*م\b)", "15normal"),

    (r"(?:iphone\s*)?14\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "14max"),
    (r"(?:iphone\s*)?14\s*(?:pro|پرو)", "14pro"),
    (r"\b14\b(?!\s*میلیون|\s*م\b)", "14normal"),

    (r"(?:iphone\s*)?13\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "13max"),
    (r"(?:iphone\s*)?13\s*(?:pro|پرو)", "13pro"),
    (r"\b13\b(?!\s*میلیون|\s*م\b)", "13normal"),

    (r"(?:iphone\s*)?12\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "12max"),
    (r"(?:iphone\s*)?12\s*(?:pro|پرو)", "12pro"),
    (r"\b12\b(?!\s*میلیون|\s*م\b)", "12normal"),

    (r"(?:iphone\s*)?11\s*(?:pro\s*max|promax|پرومکس|پرو\s*مکس)", "11max"),
    (r"(?:iphone\s*)?11\s*(?:pro|پرو)", "11pro"),
    (r"\b11\b(?!\s*میلیون|\s*م\b)", "11normal"),

    (r"(?:iphone\s*)?se\s*(?:2020|2022|3)?", "se2020"),
]


def _scan_catalog():
    """Scan iphone/ dir and return {model_prefix: [filepath, ...]}"""
    catalog = {}
    if not os.path.isdir(IPHONE_DIR):
        return catalog

    for fname in os.listdir(IPHONE_DIR):
        fpath = os.path.join(IPHONE_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = fname.lower().rsplit('.', 1)[-1]
        if ext not in ('jpg', 'jpeg', 'png', 'webp'):
            continue
        name = fname.rsplit('.', 1)[0].lower()
        parts = name.split('_', 1)
        model_key = parts[0]
        color_key = parts[1] if len(parts) > 1 else ""
        
        if model_key not in catalog:
            catalog[model_key] = []
        catalog[model_key].append({'path': fpath, 'color': color_key, 'filename': fname})

    return catalog


def _extract_model_from_text(text):
    """Extract the model prefix from post text using regex."""
    if not text:
        return None
    text_lower = str(text).lower()
    for pattern, prefix in MODEL_PATTERNS:
        if re.search(pattern, text_lower):
            return prefix
    return None


def _extract_color_from_text(text):
    """Extract color keywords from post text."""
    if not text:
        return []
    text_lower = str(text).lower()
    matched_file_keywords = []
    for color_name, file_keywords in COLOR_MAP.items():
        if color_name in text_lower:
            matched_file_keywords.extend(file_keywords)

    return list(set(matched_file_keywords))


def find_best_image(post_text):
    """
    Given a generated post text, find the best matching image from iphone/.
    
    Returns:
        str or None: absolute path to the best matching image, or None if no match.
    
    Matching priority:
        1. Exact model + exact color match
        2. Exact model, any image (random pick)
        3. None (fallback to story screenshot)
    """
    catalog = _scan_catalog()
    if not catalog:
        print("[IMAGE MATCHER] No images found in iphone/ directory.")
        return None

    model_prefix = _extract_model_from_text(post_text)
    if not model_prefix:
        print("[IMAGE MATCHER] Could not extract model from post text.")
        return None

    print(f"[IMAGE MATCHER] Detected model: {model_prefix}")

    # Find matching model group
    model_images = catalog.get(model_prefix, [])
    
    # Also check variant keys (e.g. "12" might match "12_pro_gold")
    if not model_images:
        for key, imgs in catalog.items():
            if key.startswith(model_prefix):
                model_images.extend(imgs)

    if not model_images:
        print(f"[IMAGE MATCHER] No images found for model '{model_prefix}'.")
        return None

    print(f"[IMAGE MATCHER] Found {len(model_images)} images for model '{model_prefix}'.")

    # Try to match color
    color_keywords = _extract_color_from_text(post_text)
    if color_keywords:
        print(f"[IMAGE MATCHER] Looking for colors: {color_keywords}")
        color_matches = []
        for img in model_images:
            for kw in color_keywords:
                if kw in img['color']:
                    color_matches.append(img)
                    break
        if color_matches:
            chosen = random.choice(color_matches)
            print(f"[IMAGE MATCHER] Color match: {chosen['filename']}")
            return chosen['path']

    # No color match — pick random from model
    chosen = random.choice(model_images)
    print(f"[IMAGE MATCHER] No color match, random pick: {chosen['filename']}")
    return chosen['path']
