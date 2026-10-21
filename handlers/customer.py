import logging
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
)
from core import config, database, utils
from services import inventory_service, pricing_service
from services.pricing_service import _fmt

logger = logging.getLogger(__name__)

# State constants for budget / model suggestion flow
WAIT_BUDGET_INPUT = 50

def start(update: Update, context: CallbackContext) -> None:
    """Handle /start — request phone number."""
    context.user_data.clear()
    
    keyboard = [[KeyboardButton(text="📱 تایید و ارسال شماره تماس", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    text = (
        "سلام 👋\n"
        "به ربات تخصصی دانیفون (Danifonex) خوش آمدید.\n\n"
        "برای دسترسی کامل به امکانات ربات، لطفاً شماره تماس خود را تأیید کنید:"
    )
    if update.message:
        update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        update.callback_query.message.reply_text(text, reply_markup=reply_markup)

def show_main_menu(update: Update, context: CallbackContext) -> None:
    context.user_data.clear()
    """Build and show organized inline glass main menu based on Client Panel architecture."""
    keyboard = [
        [InlineKeyboardButton("⚖️ کارشناسی و قیمت گذاری گوشی شما", callback_data="menu_pricing")],
        [InlineKeyboardButton("📱 دیدن لیست موجودی های کارکرده", callback_data="customer_used_inventory")],
        [InlineKeyboardButton("🛂 ریجستری", callback_data="customer_registry")],
        [InlineKeyboardButton("🍏 اپل آیدی", callback_data="customer_apple_id")],
        [InlineKeyboardButton("📢 چنل تلگرام", url="https://t.me/daniphoneir")],
        [InlineKeyboardButton("🎧 ارتباط با کارشناس و پشتیبانی", url=f"https://t.me/{config.EXPERT_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "💎 **پنل مشتریان دانیفون** 💎\n\n"
        "لطفاً خدمت مورد نظر خود را از دکمههای زیر انتخاب کنید:"
    )
    
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.message:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

def handle_contact(update: Update, context: CallbackContext) -> None:
    """Handle the user sharing their contact, then show main menu."""
    if not update.message or not update.message.contact:
        return
    contact = update.message.contact
    user = update.effective_user
    
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    phone_number = contact.phone_number
    
    try:
        database.add_user(user_id, username, first_name, phone_number)
    except Exception as e:
        logger.error(f"Failed to save contact to SQLite: {e}")
    
    update.message.reply_text(
        "شماره شما با موفقیت تایید شد ✅",
        reply_markup=ReplyKeyboardRemove()
    )
    show_main_menu(update, context)


def customer_registry_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("قیمت گمرکی + ریجستری", callback_data="customer_registry_prices")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="🛂 **بخش ریجستری**\n\nجهت مشاهده تعرفه گمرکی و هزینههای رجیستری اقدام کنید:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def customer_registry_prices(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎧 ارتباط با پشتیبانی جهت ثبت", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="customer_registry")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="🛂 **تعرفه گمرکی و پاسپورت**\n\nلیست قیمتها به زودی به صورت خودکار در این بخش آپدیت میشود. فعلاً جهت استعلام دقیق و ثبت پاسپورت با کارشناسان ما در ارتباط باشید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def customer_apple_id_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎧 ارتباط با پشتیبانی جهت خرید", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="🍏 **خدمات اپل آیدی دانیفون**\n\nجهت ساخت اپل آیدی کارتی معتبر و پشتیبانی، با پشتیبانان سایت در ارتباط باشید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def storefront_menu(update: Update, context: CallbackContext) -> None:
    """Show the Storefront Inventory submenu."""
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🆕 آیفونهای آکبند", callback_data="store_new")],
        [InlineKeyboardButton("🔄 آیفونهای کارکرده", callback_data="customer_used_inventory")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="به ویترین فروشگاه خوش آمدید. لطفاً دستهبندی را انتخاب کنید:",
        reply_markup=reply_markup
    )

def show_used_inventory(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    unique_models = {}
    db = inventory_service.get_storefront_inventory()
    for item in db['used'].values():
        model_name = item["model"]
        cb_data = "view_model_" + model_name.replace(" ", "").lower()
        if cb_data not in unique_models:
            unique_models[cb_data] = model_name
            
    keyboard = []
    for cb_data, display_name in unique_models.items():
        keyboard.append([InlineKeyboardButton(display_name, callback_data=cb_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="موجودی آیفونهای کارکرده:\nلطفاً مدل مورد نظر خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

def view_model_item(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    target_cb_data = query.data
    matching_items = []
    model_display_name = ""
    db = inventory_service.get_storefront_inventory()
    for item in db['used'].values():
        cb_data = "view_model_" + item["model"].replace(" ", "").lower()
        if cb_data == target_cb_data:
            matching_items.append(item)
            model_display_name = item["model"]
    
    if not matching_items:
        query.edit_message_text("موجودی برای این مدل یافت نشد.")
        return
        
    text_lines = [f"📱 **موجودی {model_display_name}**:\n"]
    for idx, item in enumerate(matching_items, start=1):
        text_lines.append(f"🔹 **مورد {idx}:**")
        text_lines.append(f"ظرفیت: {item.get('capacity', 'نامشخص')}")
        text_lines.append(f"پارت نامبر: {item.get('part', 'نامشخص')}")
        if 'sim' in item:
            text_lines.append(f"سیمکارت: {item.get('sim', 'نامشخص')}")
        if 'registry' in item:
            text_lines.append(f"رجیستری: {item.get('registry', 'نامشخص')}")
        text_lines.append(f"باتری: {item.get('battery', 'نامشخص')}%")
        text_lines.append(f"وضعیت: {item.get('condition', 'نامشخص')}")
        text_lines.append(f"قیمت: {item.get('price', 'نامشخص')} تومان\n")
        
    text = "\n".join(text_lines)
    model_key = target_cb_data.replace("view_model_", "")
    keyboard = [
        [InlineKeyboardButton("📞 ثبت سفارش و ارتباط با کارشناس", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="customer_used_inventory")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

def show_new_inventory(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    unique_models = {}
    db = inventory_service.get_storefront_inventory()
    for item in db['new'].values():
        model_name = item["model"]
        cb_data = "view_new_model_" + model_name.replace(" ", "").lower()
        if cb_data not in unique_models:
            unique_models[cb_data] = model_name
            
    keyboard = []
    for cb_data, display_name in unique_models.items():
        keyboard.append([InlineKeyboardButton(display_name, callback_data=cb_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="موجودی آیفونهای آکبند:\nلطفاً مدل مورد نظر خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

def view_new_model_item(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    target_cb_data = query.data
    matching_items = []
    model_display_name = ""
    db = inventory_service.get_storefront_inventory()
    for item in db['new'].values():
        cb_data = "view_new_model_" + item["model"].replace(" ", "").lower()
        if cb_data == target_cb_data:
            matching_items.append(item)
            model_display_name = item["model"]
    
    if not matching_items:
        query.edit_message_text("موجودی برای این مدل یافت نشد.")
        return
        
    text_lines = [f"🆕 **موجودی آکبند {model_display_name}**:\n"]
    for idx, item in enumerate(matching_items, start=1):
        text_lines.append(f"🔹 **مورد {idx}:**")
        text_lines.append(f"ظرفیت: {item.get('capacity', 'نامشخص')}")
        text_lines.append(f"پارت نامبر: {item.get('part', 'نامشخص')}")
        if 'sim' in item:
            text_lines.append(f"سیمکارت: {item.get('sim', 'نامشخص')}")
        if 'registry' in item:
            text_lines.append(f"رجیستری: {item.get('registry', 'نامشخص')}")
        text_lines.append(f"وضعیت: {item.get('condition', 'نامشخص')}")
        text_lines.append(f"قیمت: {item.get('price', 'نامشخص')} تومان\n")
        
    text = "\n".join(text_lines)
    keyboard = [
        [InlineKeyboardButton("📞 ثبت سفارش و ارتباط با کارشناس", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="store_new")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

# --- Services Pricing Menu ---
def show_services_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    text = (
        "🛠️ **تعرفه خدمات تخصصی دانیفون (Danifon Services)** 🛠️\n\n"
        "📌 **خدمات اپل آیدی (Apple ID):**\n"
        "• **پلن ۱: اپل آیدی شخصی (معمولی)**\n"
        "  - ساخته شده با نام، نامخانوادگی و جیمیل شخصی شما\n"
        "  - 💵 **قیمت:** ۱,۸۰۰,۰۰۰ تومان\n\n"
        "• **پلن ۲: اپل آیدی اختصاصی (با گارانتی)**\n"
        "  - پشتیبانی کامل + گارانتی بازیابی و عدم قفل شدن\n"
        "  - 💵 **قیمت:** ۲,۸۰۰,۰۰۰ تومان\n\n"
        "📌 **خدمات آنلاک و رجیستری:**\n"
        "• استعلام پاسپورت و ثبت گمرکی: تماس بگیرید\n\n"
        "برای ثبت سفارش هر یک از پلنها، مستقیماً به کارشناس پیام دهید 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("📞 ثبت سفارش و ارتباط با کارشناس (@danikamali)", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

# --- Budget Recommendations Flow ---
def start_recommendations_flow(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    quote_info = context.user_data.get("last_calculated_quote")
    if quote_info and quote_info.get("sell_price"):
        base_price = quote_info["sell_price"]
        max_budget = base_price + 60_000_000
        return _show_suggestions_for_budget(update, context, max_budget, base_price)

    query.edit_message_text(
        "💡 **پیشنهاد مدل بر اساس بودجه**\n\n"
        "لطفاً حداکثر بودجه خود به تومان را وارد کنید:\n"
        "*(مثلاً: 65000000 یا 65 میلیون)*"
    )
    return WAIT_BUDGET_INPUT

def receive_budget_input(update: Update, context: CallbackContext) -> int:
    if not update.message or not update.message.text:
        return WAIT_BUDGET_INPUT

    try:
        from core.security import sanitize_amount
        budget = sanitize_amount(update.message.text)
    except Exception:
        update.message.reply_text("❌ لطفاً بودجه را به صورت عدد معتبر وارد کنید:")
        return WAIT_BUDGET_INPUT

    if budget <= 0:
        update.message.reply_text("❌ مبلغ وارد شده باید بزرگتر از صفر باشد:")
        return WAIT_BUDGET_INPUT

    _show_suggestions_for_budget(update, context, budget)
    return ConversationHandler.END

def _show_suggestions_for_budget(update: Update, context: CallbackContext, max_budget: float, base_phone_price: float = 0.0) -> int:
    mp_table = pricing_service._load_mp_table()
    db_inventory = inventory_service.get_storefront_inventory()

    matching_models = []
    
    # 1. Search in live inventory items
    for item_type in ['used', 'new']:
        for item_id, item in db_inventory[item_type].items():
            try:
                clean_p_str = re.sub(r"[^\d]", "", str(item.get("price", "0")))
                p_val = float(clean_p_str) if clean_p_str else 0.0
                if p_val > 0 and (base_phone_price <= p_val <= max_budget):
                    matching_models.append({
                        "name": f"{item.get('model')} {item.get('capacity')} ({item_type.upper()})",
                        "price": p_val,
                        "source": "موجود در انبار"
                    })
            except Exception:
                pass

    # 2. Search in base mp_table if inventory matches are few
    if len(matching_models) < 4:
        for model_name, cap_map in mp_table.items():
            for cap, price in cap_map.items():
                p_val = float(price)
                if base_phone_price > 0:
                    min_target = base_phone_price
                    max_target = base_phone_price + 60_000_000
                else:
                    min_target = max_budget * 0.70
                    max_target = max_budget

                if min_target <= p_val <= max_target:
                    matching_models.append({
                        "name": f"{model_name} {cap}",
                        "price": p_val,
                        "source": "قیمت مرجع بازار"
                    })

    # Sort by price ascending
    matching_models.sort(key=lambda x: x["price"])
    seen = set()
    unique_matches = []
    for m in matching_models:
        if m["name"] not in seen:
            seen.add(m["name"])
            unique_matches.append(m)

    top_matches = unique_matches[:6]

    if base_phone_price > 0:
        header = (
            f"🎯 **پیشنهاد ارتقا بر اساس قیمت گوشی شما** 🎯\n"
            f"▫️ **قیمت پایه گوشی شما:** {_fmt(int(base_phone_price))} تومان\n"
            f"▫️ **بازه پیشنهادی (تا ۶۰ میلیون بالاتر):** {_fmt(int(base_phone_price))} تا {_fmt(int(max_budget))} تومان\n\n"
        )
    else:
        header = (
            f"🎯 **مدلهای پیشنهادی تا سقف بودجه {_fmt(int(max_budget))} تومان:** 🎯\n\n"
        )

    if not top_matches:
        text = header + "متاسفانه مدلی دقیقا در این بازه قیمتی یافت نشد. میتوانید با کارشناس ما مشورت کنید."
    else:
        lines = [header]
        for idx, item in enumerate(top_matches, start=1):
            lines.append(f"{idx}. **{item['name']}**")
            lines.append(f"   💵 قیمت: {_fmt(int(item['price']))} تومان ({item['source']})")
        lines.append("\n📞 برای ثبت سفارش یا تعویض گوشی به کارشناس پیام دهید:")
        text = "\n".join(lines)

    keyboard = [
        [InlineKeyboardButton("📞 ارتباط با کارشناس (@danikamali)", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.message:
        update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Handle /cancel — gracefully exit the conversation."""
    context.user_data.clear()
    update.message.reply_text(
        "❌ عملیات لغو شد. برای نمایش منوی اصلی /start را بزنید.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

def fallback_unknown(update: Update, context: CallbackContext) -> None:
    """Handle unexpected messages outside of a conversation."""
    if not update or not update.message or not update.effective_chat:
        return
    if update.effective_chat.type != 'private':
        return
    if context.user_data and context.user_data.get('awaiting_ai_price'):
        from handlers.pricing import handle_ai_price_input
        return handle_ai_price_input(update, context)
        
    try:
        update.message.reply_text(
            "👋 برای نمایش منوی اصلی /start را بزنید.",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        logger.warning(f"Could not reply in fallback_unknown: {e}")
