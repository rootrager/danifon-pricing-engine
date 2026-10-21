import re
import math
import logging
from functools import wraps
from typing import Any, Callable
from telegram import Update
from telegram.ext import CallbackContext
from core.config import AUTHORIZED_ADMINS

logger = logging.getLogger(__name__)

PERSIAN_TO_ENGLISH = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '۴': '4',
    '۵': '5', '۶': '6', '٧': '7', '٨': '8', '٩': '9',
}

def is_authorized_admin(user_id: int) -> bool:
    """Checks if Telegram user_id is in AUTHORIZED_ADMINS whitelist."""
    return user_id in AUTHORIZED_ADMINS

def admin_required(func: Callable) -> Callable:
    """Decorator to enforce admin authorization on Telegram handlers."""
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        if not user or not is_authorized_admin(user.id):
            logger.warning(f"Unauthorized access attempt by user: {user.id if user else 'Unknown'}")
            if update.callback_query:
                update.callback_query.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
            elif update.message:
                update.message.reply_text("⛔ شما به این بخش دسترسی ندارید.")
            return None
        return func(update, context, *args, **kwargs)
    return wrapper

def sanitize_imei(imei: Any) -> str:
    """Validates and strips spaces/hyphens from IMEI strings."""
    if not imei:
        raise ValueError("IMEI cannot be empty.")
    clean = re.sub(r'[\s\-]', '', str(imei))
    if not clean.isdigit() or len(clean) < 8 or len(clean) > 20:
        raise ValueError(f"Invalid IMEI format: {imei}")
    return clean

def sanitize_amount(val: Any) -> float:
    """Validates numeric amounts and handles Persian/Arabic digits."""
    if val is None:
        raise ValueError("Amount cannot be None.")
    if isinstance(val, str):
        cleaned = "".join(PERSIAN_TO_ENGLISH.get(ch, ch) for ch in str(val).replace(",", "").strip())
        val = float(cleaned)
    else:
        val = float(val)
        
    if math.isnan(val) or math.isinf(val):
        raise ValueError("Amount cannot be NaN or Infinite.")
    if val < 0:
        raise ValueError("Amount cannot be negative.")
    return val

def sanitize_text(text: Any, max_len: int = 1000) -> str:
    """Strips whitespace and enforces length boundaries on text."""
    if text is None:
        return ""
    clean = str(text).strip()
    return clean[:max_len]
