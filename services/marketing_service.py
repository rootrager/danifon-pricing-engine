import json
import os
import re
import requests
import logging
from typing import Dict, Any, Tuple
from core import config

logger = logging.getLogger(__name__)

def get_channel_keyboard() -> Dict[str, Any]:
    """Builds channel inline keyboard with expert contact link."""
    return {
        "inline_keyboard": [
            [{"text": "ارتباط با کارشناس 📞", "url": f"https://t.me/{config.EXPERT_USERNAME}"}]
        ]
    }

def format_channel_price(val: Any) -> str:
    """Format any price value into standard DaniFone channel thousands format (e.g. 129.000 or 53.000)."""
    s_val = str(val).strip()
    clean = re.sub(r"[^\d]", "", s_val)
    if not clean:
        return s_val
    num = int(clean)
    if num >= 1_000_000:
        in_thousands = num // 1000
        return f"{in_thousands:,}".replace(",", ".")
    elif num < 1000:
        in_thousands = num * 1000
        return f"{in_thousands:,}".replace(",", ".")
    else:
        return f"{num:,}".replace(",", ".")

def format_danifon_channel_post(
    model: str,
    condition: str = "کارکرده",
    color: str = "آبی سیرا",
    capacity: str = "128GB",
    part: str = "LL/A",
    sim: str = "تک سیمکارت",
    registry: str = "رجیستر شده",
    battery: str = "83%",
    price: str = "129.000"
) -> str:
    """Builds DaniFone channel post matching the exact standard layout."""
    channel_link = "https://t.me/daniphoneir"
    
    if capacity and capacity.isdigit():
        capacity = f"{capacity}GB"
    elif capacity and capacity.upper().endswith("G") and not capacity.upper().endswith("GB"):
        capacity = capacity[:-1] + "GB"
        
    if battery and battery.isdigit():
        battery = f"{battery}%"
        
    price_fmt = format_channel_price(price)
    
    post_text = (
        f'● <a href="{channel_link}">DaniFone</a> | Apple Store\n\n'
        f"📱 {model}\n\n"
        f"▪️ ظرفیت: {capacity}\n"
        f"▪️ رنگ: {color}\n"
        f"▪️ وضعیت: {condition}\n"
        f"▪️ باتری: {battery}\n"
        f"▪️ پارتنامبر و سیمکارت: {part} | {sim}\n"
        f"▪️ رجیستری: {registry}\n\n"
        f"🏷 قیمت: {price_fmt} تومان\n\n"
        f"🆔 @daniphoneir"
    )
    return post_text

def parse_specs_from_text(text: str) -> Dict[str, str]:
    """Defensively parses specs from freeform admin input into post fields."""
    text_clean = text.strip()
    
    # Model extraction (supports both English iPhone and Persian آیفون / پرو / مکس / پلاس / مینی)
    m_match = re.search(r"((?:iPhone|آیفون)\s*\d+\s*(?:Pro\s*Max|پرو\s*مکس|Pro|پرو|Plus|پلاس|Mini|مینی)?|(?:iPhone|آیفون)\s*X[SR]?\s*(?:Max|مکس)?)", text_clean, re.IGNORECASE)
    if m_match:
        raw_m = m_match.group(1)
        model = re.sub(r"آیفون", "iPhone", raw_m, flags=re.IGNORECASE)
        model = re.sub(r"پرو\s*مکس", "Pro Max", model, flags=re.IGNORECASE)
        model = re.sub(r"پرو", "Pro", model, flags=re.IGNORECASE)
        model = re.sub(r"مکس", "Max", model, flags=re.IGNORECASE)
        model = re.sub(r"پلاس", "Plus", model, flags=re.IGNORECASE)
        model = re.sub(r"مینی", "Mini", model, flags=re.IGNORECASE)
        model = re.sub(r"iphone", "iPhone", model, flags=re.IGNORECASE)
        model = re.sub(r"pro", "Pro", model, flags=re.IGNORECASE)
        model = re.sub(r"max", "Max", model, flags=re.IGNORECASE)
        model = re.sub(r"plus", "Plus", model, flags=re.IGNORECASE)
        model = re.sub(r"mini", "Mini", model, flags=re.IGNORECASE)
    else:
        model = "iPhone 13 Pro Max"
        
    condition = "آکبند" if any(w in text_clean for w in ["آکبند", "نو", "akband"]) else "کارکرده"
    
    cap_match = re.search(r"(\d{3,4}\s*GB|\d{3,4}\s*G|1TB|1TB|64|128|256|512)", text_clean, re.IGNORECASE)
    cap = cap_match.group(1).upper() if cap_match else "128GB"
    
    part_match = re.search(r"\b(LL/A|ZA|CH|LA|TH|LL)\b", text_clean, re.IGNORECASE)
    part = part_match.group(1).upper() if part_match else "LL/A"
    
    sim = "دو سیمکارت" if any(w in text_clean.lower() for w in ["دو سیم", "2sim", "dual"]) else "تک سیمکارت"
    reg = "بدون رجیستر" if any(w in text_clean for w in ["بدون رجیستر", "بدون کد", "unregistered"]) else "رجیستر شده"
    
    bat_match = re.search(r"باتری\s*(\d{2,3})|battery\s*(\d{2,3})|(\d{2,3})%", text_clean, re.IGNORECASE)
    if bat_match:
        bat_val = bat_match.group(1) or bat_match.group(2) or bat_match.group(3)
        battery = f"{bat_val}%"
    else:
        battery = "100%" if condition == "آکبند" else "83%"
        
    color_keywords = {
        "آبی سیرا": ["آبی سیرا", "sierra blue", "سیرا"],
        "آبی": ["آبی", "blue"],
        "مشکی": ["مشکی", "black", "سیاه", "جرمنی"],
        "سفید": ["سفید", "white", "استارلایت"],
        "نچرال تیتانیوم": ["نچرال تیتانیوم", "natural titanium", "نچرال"],
        "دزرت تیتانیوم": ["دزرت تیتانیوم", "desert titanium", "دزرت"],
        "بنفش": ["بنفش", "purple", "دیپ پرپل"],
        "طلایی": ["طلایی", "gold"],
        "صورتی": ["صورتی", "pink"],
        "خاکستری": ["خاکستری", "space gray", "خاکستری فضایی"]
    }
    found_color = "آبی سیرا" if condition == "کارکرده" and "13" in model else "مشکی"
    for c_name, kw_list in color_keywords.items():
        if any(kw in text_clean.lower() for kw in kw_list):
            found_color = c_name
            break
            
    price_match = re.search(r"قیمت\s*[:\s]*([\d\.\,\s]+(?:میلیون|m)?)|(\d{2,3}[\.\,]\d{3})|(\d{7,9})", text_clean, re.IGNORECASE)
    if price_match:
        raw_price = price_match.group(1) or price_match.group(2) or price_match.group(3)
        price = format_channel_price(raw_price)
    else:
        price = "129.000"
        
    return {
        "model": model,
        "condition": condition,
        "color": found_color,
        "capacity": cap,
        "part": part,
        "sim": sim,
        "registry": reg,
        "battery": battery,
        "price": price
    }

def create_channel_post_from_text_spec(raw_text: str) -> Dict[str, Any]:
    """
    Builds a channel post directly from admin text spec matching the exact DaniFone channel format.
    Picks matching photo from local iphone/ folder using image_matcher.
    """
    import re
    from image_matcher import find_best_image
    image_path = find_best_image(raw_text)
    
    specs = parse_specs_from_text(raw_text)
    post_text = format_danifon_channel_post(
        model=specs["model"],
        condition=specs["condition"],
        color=specs["color"],
        capacity=specs["capacity"],
        part=specs["part"],
        sim=specs["sim"],
        registry=specs["registry"],
        battery=specs["battery"],
        price=specs["price"]
    )
    
    return {
        "text": post_text,
        "image_path": image_path
    }

def publish_post_detailed(chat_id: Any, text: str, image_path: str = None, channel_id: str = None) -> (bool, str):
    """
    Publishes a photo with caption (or text message if photo missing) and keyboard to the target Telegram channel.
    Returns tuple of (success: bool, detail_message: str).
    """
    target_channel = channel_id or config.CHANNEL_ID
    channel_kb = get_channel_keyboard()
    last_error = ""

    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as f:
                payload = {
                    "chat_id": target_channel,
                    "caption": text,
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(channel_kb)
                }
                res = requests.post(
                    f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data=payload,
                    files={"photo": f},
                    proxies=config.TELEGRAM_PROXY,
                    timeout=30.0
                )
                res_data = res.json()
                if res_data.get("ok"):
                    return True, "منتشر شد."
                last_error = res_data.get("description", str(res_data))
                logger.warning(f"Telegram sendPhoto to {target_channel} failed: {res_data}, fallback to sendMessage")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Failed to send photo to {target_channel}: {e}, fallback to sendMessage")

    # Text fallback or text-only post
    try:
        payload = {
            "chat_id": target_channel,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(channel_kb)
        }
        res = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            data=payload,
            proxies=config.TELEGRAM_PROXY,
            timeout=30.0
        )
        res_data = res.json()
        if not res_data.get("ok"):
            err_desc = res_data.get("description", str(res_data))
            logger.error(f"Telegram sendMessage failed: {res_data}")
            return False, err_desc
        return True, "منتشر شد."
    except Exception as e:
        logger.error(f"Failed to publish post to channel {target_channel}: {e}")
        return False, str(e)

def publish_post(chat_id: Any, text: str, image_path: str = None, channel_id: str = None) -> bool:
    """Publishes post and returns boolean success status for backward compatibility."""
    success, _ = publish_post_detailed(chat_id, text, image_path, channel_id)
    return success

DEFAULT_BROADCAST_TEMPLATE = (
    "سلام {name} عزیز، دانیال هستم از دانیفون 👋\n\n"
    "این چند روز با جهش قیمت دلار، خیلی از بچهها پیام میدادن و نگران اوضاع بودند. خواستم کوتاه و رفیقونه بهت بگم:\n\n"
    "توی این تورم شدید، متاسفانه نگهداشتن ریال یعنی کم شدن روزانه قدرت خریدت. اگر هر برنامهای برای خرید یا ارتقای گوشیت داری، پیشنهاد میکنم زودتر تکلیفت رو مشخص کنی و به فردا نندازی؛ بازار توی این اوضاع صبر نمیکنه.\n\n"
    "ما توی دانیفون مثل همیشه کنارتون هستیم. فقط خواستم این نکته رو بهت بگم تا توی این نوسانات بازار متضرر نشی ❤️\n\n"
    "اگر سوالی داشتی یا راهنمایی میخواستی، مستقیماً همینجا پیام بده."
)

def get_broadcast_users():
    """Fetches all registered users from database (User_ID, First_Name)."""
    from core import database
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT User_ID, First_Name FROM Users ORDER BY Date_Joined DESC")
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Error fetching broadcast users: {e}")
        return []
    finally:
        conn.close()

def execute_broadcast_job(bot, admin_chat_id: int, text_template: str):
    """
    Executes a mass broadcast to all registered users in a background thread.
    Safely handles rate limits, user blocks, and sends progress/summary to admin_chat_id.
    """
    import time
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.error import Unauthorized, TelegramError

    users = get_broadcast_users()
    total_users = len(users)
    if total_users == 0:
        bot.send_message(chat_id=admin_chat_id, text="⚠️ هیچ کاربری برای ارسال پیام یافت نشد.")
        return

    start_time = time.time()
    success_count = 0
    blocked_count = 0
    failed_count = 0

    expert_username = getattr(config, "EXPERT_USERNAME", "daniphoneir")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 گفتوگو با دانیال", url=f"https://t.me/{expert_username}")]
    ])

    for user_id, first_name in users:
        raw_name = (first_name or "").strip()
        name = raw_name if raw_name else "دوست"
        
        try:
            user_msg = text_template.format(name=name)
        except Exception:
            user_msg = text_template.replace("{name}", name)

        sent = False
        attempts = 0
        while not sent and attempts < 3:
            attempts += 1
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=user_msg,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
                success_count += 1
                sent = True
                time.sleep(0.05)
            except Unauthorized:
                blocked_count += 1
                sent = True
            except TelegramError as e:
                err_str = str(e).lower()
                if "retry after" in err_str or "flood" in err_str:
                    logger.warning(f"Flood control limit reached during broadcast. Sleeping for 5s")
                    time.sleep(5)
                elif "blocked" in err_str or "user is deactivated" in err_str:
                    blocked_count += 1
                    sent = True
                else:
                    logger.warning(f"TelegramError sending broadcast to {user_id}: {e}")
                    if attempts >= 3:
                        failed_count += 1
                    else:
                        time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error sending broadcast to {user_id}: {e}")
                failed_count += 1
                sent = True

    elapsed = time.time() - start_time
    summary_text = (
        "📊 **گزارش نهایی ارسال پیام همگانی (Broadcast)**\n\n"
        f"👥 کل مخاطبان: **{total_users} نفر**\n"
        f"✅ ارسال موفق: **{success_count}**\n"
        f"🚫 بلاک شده / غیرفعال: **{blocked_count}**\n"
        f"❌ خطا در ارسال: **{failed_count}**\n"
        f"⏱ زمان کل: **{elapsed:.1f} ثانیه**"
    )
    try:
        bot.send_message(chat_id=admin_chat_id, text=summary_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send broadcast summary to admin: {e}")

