import requests
import base64
import os
import json
import logging
from typing import Tuple, Dict, Any, Optional
from core import config
from core import database
from color_detector import detect_phone_color, correct_color_in_post
from image_matcher import find_best_image

logger = logging.getLogger(__name__)

def parse_llm_response(response) -> Dict[str, Any]:
    """Defensively parses standard JSON or 9Router SSE streaming format."""
    raw_text = response.text.strip()
    if raw_text.startswith("data:"):
        full_content = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content") or choices[0].get("message", {}).get("content")
                        if content:
                            full_content.append(content)
                except Exception:
                    pass
        combined = "".join(full_content).strip()
        return {"choices": [{"message": {"content": combined}}]}
    else:
        return response.json()

def _call_llm(payload_factory, timeout: int = 90) -> Tuple[str, Dict[str, Any]]:
    """Try the primary Vision model, then each fallback on 429/5xx."""
    models = [config.VISION_LLM_MODEL] + list(config.VISION_LLM_FALLBACKS)
    seen, chain = set(), []
    for m in models:
        if m and m not in seen and not m.startswith("auto/"):
            seen.add(m)
            chain.append(m)

    last_err = None
    for model in chain:
        try:
            payload = payload_factory(model)
            response = requests.post(
                config.VISION_LLM_URL,
                json=payload,
                proxies=config.NO_PROXY,
                timeout=timeout,
            )
            if response.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"[LLM] {model} -> HTTP {response.status_code}, trying fallback...")
                last_err = f"HTTP {response.status_code}"
                continue
            response.raise_for_status()
            data = parse_llm_response(response)
            return model, data
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code in (429, 500, 502, 503, 504):
                logger.warning(f"[LLM] {model} -> HTTP {code}, trying fallback...")
                last_err = f"HTTP {code}"
                continue
            raise
        except Exception as e:
            last_err = str(e)
            logger.warning(f"[LLM] {model} -> {e}, trying fallback...")
            continue

    raise RuntimeError(f"All {len(chain)} models failed. Last error: {last_err}")

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_inventory_text_from_photo(image_path: str) -> str:
    """
    Analyzes a daily inventory list photo (table/text list) using Vision LLM.
    Returns structured text lines for inventory ingestion.
    """
    if not os.path.exists(image_path):
        return ""

    base64_image = encode_image_to_base64(image_path)
    system_prompt = """You are an OCR and inventory processing assistant for an iPhone retail store in Iran.
Analyze the provided image of daily phone inventory (price list, whiteboard, notebook, paper list, or screen screenshot).
Extract every phone item listed with its details:
- iPhone Model (e.g. 16 Pro Max, 15 Pro, 13 Normal)
- Storage Capacity (e.g. 128, 256, 512, 1TB)
- Part Number (e.g. ZA, CH, LL)
- Battery Health % if visible (e.g. 95)
- Registry Status if visible (کددار / بدون کد / رجیستر)
- Price in Toman (e.g. 235000000 or 235,000,000 or 235m)

Output ONE item per line in clear Persian/English format like:
16 Pro Max 256 ZA - 235000000
15 Pro 128 LL - 145000000
13 Normal 128 CH battery 88 - 75000000

Output ONLY the extracted inventory text lines, nothing else. Do not add headers or commentary."""

    try:
        model_used, data = _call_llm(lambda m: {
            "model": m,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "لطفاً تمام لیست موجودی و قیمتهای درون این تصویر را استخراج کن."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
        })
        text_out = data['choices'][0]['message']['content'].strip()
        logger.info(f"[VISION-INVENTORY] Extracted inventory using model: {model_used}")
        return text_out
    except Exception as e:
        logger.error(f"[ERROR] Inventory photo extraction failed: {e}")
        return ""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_post_from_image(image_path: str) -> str:
    """
    Analyzes phone photo or story screenshot with Vision LLM and HSV pixel analysis.
    Returns formatted Persian post text.
    """
    if not os.path.exists(image_path):
        return "⚠️ تصویر یافت نشد."

    base64_image = encode_image_to_base64(image_path)
    recent_feedback = database.get_recent_story_feedback(limit=3)
    feedback_context = ""
    if recent_feedback:
        feedback_context = "\n\nPast Admin corrections to learn from:\n" + "\n".join([f"- {f}" for f in recent_feedback])

    system_prompt = f"""You are a professional e-commerce copywriter for DaniFone.ir Telegram channel selling iPhones in Iran.

Analyze the provided screenshot of a Telegram story or product photo.
Extract ALL visible details: device model, color, storage, condition, battery health, price, SIM info, registry status, part number, etc.

CRITICAL COLOR RULES:
- Use these Persian color names only: مشکی / سفید / آبی / سبز / نارنجی / بنفش / طلایی / نچرال / دزرت تیتانیوم / صورتی / قرمز / خاکستری

You MUST output the post in EXACTLY this HTML format matching DaniFone channel template:
<a href="https://t.me/daniphoneir">DaniFone.ir | اپل استور | آیفون</a>

📱 [Device Model Name - e.g. iPhone 11]

وضعیت: [کارکرده / نو]
رنگ: [نام رنگ به فارسی]
ظرفیت: [e.g. 128GB]
پارتنامبر: [e.g. LL/A or ZA]
سیمکارت: [تک سیمکارت / دو سیمکارت]
رجیستری: [رجیستر شده / رجیستر نشده]
باتری: [e.g. 100%]

قیمت: [e.g. 53.000]

RULES:
- Output ONLY the post text in HTML, nothing else. No explanations, no markdown tags like ```.
- Format price using dots for thousands (e.g. 53.000 or 172.000).
- Do NOT add any contact or link lines at the bottom — those are handled separately by Telegram inline button.
{feedback_context}"""

    try:
        model_used, data = _call_llm(lambda m: {
            "model": m,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "از روی این اسکرین‌شات یک پست تلگرامی بساز."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        })
        post_text = data['choices'][0]['message']['content'].strip()
        logger.info(f"[VISION] Post generated with model: {model_used}")
    except Exception as e:
        logger.error(f"[ERROR] Vision LLM call failed: {e}")
        return "⚠️ خطا: تولید پست از تصویر ناموفق بود. اتصال LLM را بررسی کنید."

    # Pixel-based color verification
    try:
        detected_color, confidence = detect_phone_color(image_path)
        if confidence >= 0.55:
            corrected = correct_color_in_post(post_text, detected_color)
            if corrected != post_text:
                logger.info(f"[COLOR] Color corrected to {detected_color} (confidence={confidence:.2f})")
            post_text = corrected
    except Exception as e:
        logger.warning(f"[COLOR] Color detection skipped: {e}")

    return post_text

def revise_post_with_feedback(current_draft: str, feedback: str) -> str:
    """Revises a draft based on admin textual feedback."""
    system_prompt = """You are a professional e-commerce copywriter for a Persian Telegram channel.
Revise the provided post draft exactly as the Admin requests.
Keep the same format structure. Output ONLY the revised post text, nothing else."""

    try:
        model_used, data = _call_llm(lambda m: {
            "model": m,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"پست فعلی:\n{current_draft}\n\nدرخواست ادمین:\n{feedback}\n\nپست اصلاح‌شده را بنویس."}
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }, timeout=60)
        logger.info(f"[VISION] Revision completed with model: {model_used}")
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"[ERROR] LLM revision failed: {e}")
        return "⚠️ خطا: اصلاح پست ناموفق بود."
