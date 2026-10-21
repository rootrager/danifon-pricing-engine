import re
import os
import uuid
import json
import logging
from core.security import admin_required
from telegram import (
    Update,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)
from core import config, database, utils
from ai import engine as ai_engine
from services import pricing_service

logger = logging.getLogger(__name__)

# Conversation Handler States for Pricing Wizard (using distinct offsets to prevent state collision)
(
    PRICING_SELECT_SERIES,
    PRICING_SELECT_MODEL,
    PRICING_SELECT_STORAGE,
    PRICING_SELECT_BATTERY,
    PRICING_SELECT_REGISTRY,
    PRICING_SELECT_PART,
    PRICING_SELECT_CONDITION,
    WAITING_FOR_ADMIN_FEEDBACK,
) = range(100, 108)

# Backward compatibility aliases
SELECT_SERIES = PRICING_SELECT_SERIES
SELECT_MODEL = PRICING_SELECT_MODEL
SELECT_STORAGE = PRICING_SELECT_STORAGE
SELECT_BATTERY = PRICING_SELECT_BATTERY
SELECT_REGISTRY = PRICING_SELECT_REGISTRY
SELECT_PART = PRICING_SELECT_PART
SELECT_CONDITION = PRICING_SELECT_CONDITION

# --- HELPER KEYBOARD BUILDERS ---

def _build_series_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📱 سری ۱۷", callback_data="pricing_series_17"),
            InlineKeyboardButton("📱 سری ۱۶", callback_data="pricing_series_16"),
        ],
        [
            InlineKeyboardButton("📱 سری ۱۵", callback_data="pricing_series_15"),
            InlineKeyboardButton("📱 سری ۱۴", callback_data="pricing_series_14"),
        ],
        [
            InlineKeyboardButton("📱 سری ۱۳", callback_data="pricing_series_13"),
            InlineKeyboardButton("📱 سری ۱۲", callback_data="pricing_series_12"),
        ],
        [
            InlineKeyboardButton("📱 سری ۱۱", callback_data="pricing_series_11"),
            InlineKeyboardButton("📱 XS / XR / X / ۸", callback_data="pricing_series_older"),
        ],
        [InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_model_keyboard(series: str):
    buttons = []
    if series == "17":
        buttons = [
            [InlineKeyboardButton("👑 iPhone 17 Pro Max", callback_data="pricing_model_iPhone 17 Pro Max")],
            [InlineKeyboardButton("⭐️ iPhone 17 Pro", callback_data="pricing_model_iPhone 17 Pro")],
            [InlineKeyboardButton("📱 iPhone 17", callback_data="pricing_model_iPhone 17")],
        ]
    elif series == "16":
        buttons = [
            [
                InlineKeyboardButton("iPhone 16 Pro Max", callback_data="pricing_model_iPhone 16 Pro Max"),
                InlineKeyboardButton("iPhone 16 Pro", callback_data="pricing_model_iPhone 16 Pro"),
            ],
            [
                InlineKeyboardButton("iPhone 16 Plus", callback_data="pricing_model_iPhone 16 Plus"),
                InlineKeyboardButton("iPhone 16", callback_data="pricing_model_iPhone 16"),
            ],
        ]
    elif series == "15":
        buttons = [
            [
                InlineKeyboardButton("iPhone 15 Pro Max", callback_data="pricing_model_iPhone 15 Pro Max"),
                InlineKeyboardButton("iPhone 15 Pro", callback_data="pricing_model_iPhone 15 Pro"),
            ],
            [
                InlineKeyboardButton("iPhone 15 Plus", callback_data="pricing_model_iPhone 15 Plus"),
                InlineKeyboardButton("iPhone 15", callback_data="pricing_model_iPhone 15"),
            ],
        ]
    elif series == "14":
        buttons = [
            [
                InlineKeyboardButton("iPhone 14 Pro Max", callback_data="pricing_model_iPhone 14 Pro Max"),
                InlineKeyboardButton("iPhone 14 Pro", callback_data="pricing_model_iPhone 14 Pro"),
            ],
            [
                InlineKeyboardButton("iPhone 14 Plus", callback_data="pricing_model_iPhone 14 Plus"),
                InlineKeyboardButton("iPhone 14", callback_data="pricing_model_iPhone 14"),
            ],
        ]
    elif series == "13":
        buttons = [
            [
                InlineKeyboardButton("iPhone 13 Pro Max", callback_data="pricing_model_iPhone 13 Pro Max"),
                InlineKeyboardButton("iPhone 13 Pro", callback_data="pricing_model_iPhone 13 Pro"),
            ],
            [
                InlineKeyboardButton("iPhone 13", callback_data="pricing_model_iPhone 13"),
                InlineKeyboardButton("iPhone 13 mini", callback_data="pricing_model_iPhone 13 mini"),
            ],
        ]
    elif series == "12":
        buttons = [
            [
                InlineKeyboardButton("iPhone 12 Pro Max", callback_data="pricing_model_iPhone 12 Pro Max"),
                InlineKeyboardButton("iPhone 12 Pro", callback_data="pricing_model_iPhone 12 Pro"),
            ],
            [
                InlineKeyboardButton("iPhone 12", callback_data="pricing_model_iPhone 12"),
                InlineKeyboardButton("iPhone 12 mini", callback_data="pricing_model_iPhone 12 mini"),
            ],
        ]
    elif series == "11":
        buttons = [
            [
                InlineKeyboardButton("iPhone 11 Pro Max", callback_data="pricing_model_iPhone 11 Pro Max"),
                InlineKeyboardButton("iPhone 11 Pro", callback_data="pricing_model_iPhone 11 Pro"),
            ],
            [InlineKeyboardButton("iPhone 11", callback_data="pricing_model_iPhone 11")],
        ]
    else:  # older
        buttons = [
            [
                InlineKeyboardButton("iPhone XS Max", callback_data="pricing_model_iPhone XS Max"),
                InlineKeyboardButton("iPhone XS", callback_data="pricing_model_iPhone XS"),
            ],
            [
                InlineKeyboardButton("iPhone XR", callback_data="pricing_model_iPhone XR"),
                InlineKeyboardButton("iPhone X", callback_data="pricing_model_iPhone X"),
            ],
            [InlineKeyboardButton("iPhone 8 Plus", callback_data="pricing_model_iPhone 8 Plus")],
        ]

    buttons.append([
        InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_series"),
        InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
    ])
    return InlineKeyboardMarkup(buttons)

def _build_storage_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💾 128GB", callback_data="pricing_cap_128"),
            InlineKeyboardButton("💾 256GB", callback_data="pricing_cap_256"),
        ],
        [
            InlineKeyboardButton("💾 512GB", callback_data="pricing_cap_512"),
            InlineKeyboardButton("💾 1TB", callback_data="pricing_cap_1TB"),
        ],
        [InlineKeyboardButton("💾 64GB", callback_data="pricing_cap_64")],
        [
            InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_model"),
            InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_battery_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔋 ۱۰۰٪ (فابریک / در حد آک)", callback_data="pricing_bat_100")],
        [InlineKeyboardButton("🔋 ۹۰٪ تا ۹۹٪ (سلامت عالی)", callback_data="pricing_bat_95")],
        [InlineKeyboardButton("🔋 ۸۰٪ تا ۸۹٪ (سلامت نرمال)", callback_data="pricing_bat_85")],
        [InlineKeyboardButton("🔋 زیر ۸۰٪ (نیاز به تعویض)", callback_data="pricing_bat_75")],
        [InlineKeyboardButton("🔄 باتری تعویضی (۱۰۰٪ تعویض)", callback_data="pricing_bat_replaced")],
        [
            InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_storage"),
            InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_registry_keyboard():
    keyboard = [
        [InlineKeyboardButton("🟢 کددار (با رجیستر رسمی)", callback_data="pricing_reg_Registered")],
        [InlineKeyboardButton("🔴 بدون کد (بدون رجیستر)", callback_data="pricing_reg_Unregistered")],
        [InlineKeyboardButton("📄 مصوبه کد ملی (ثبت بدون پاسپورت)", callback_data="pricing_reg_NationalID")],
        [
            InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_battery"),
            InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_part_keyboard():
    keyboard = [
        [InlineKeyboardButton("🇹🇼 ZA/A (دو سیمکارت)", callback_data="pricing_part_ZA/A")],
        [InlineKeyboardButton("🇨🇳 CH/A (دو سیمکارت)", callback_data="pricing_part_CH/A")],
        [InlineKeyboardButton("🇺🇸 LL/A (تک سیمکارت / eSIM)", callback_data="pricing_part_LL/A")],
        [InlineKeyboardButton("🌐 سایر پارتنامبرها", callback_data="pricing_part_OTHER")],
        [
            InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_registry"),
            InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def _build_condition_keyboard():
    keyboard = [
        [InlineKeyboardButton("✨ تمیز و بدون خط و خش (Clean)", callback_data="pricing_cond_Clean")],
        [InlineKeyboardButton("🔨 درب پشت تعویض شده", callback_data="pricing_cond_BackGlass")],
        [InlineKeyboardButton("📱 السیدی تعویض شده", callback_data="pricing_cond_LCD")],
        [InlineKeyboardButton("🔧 تعویضی / خط و خش بدنه", callback_data="pricing_cond_Repaired")],
        [
            InlineKeyboardButton("🔙 مرحله قبل", callback_data="pricing_back_to_part"),
            InlineKeyboardButton("❌ انصراف", callback_data="pricing_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- WIZARD FLOW HANDLERS ---

def start_pricing_wizard(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['wizard_specs'] = {}
    
    msg_text = (
        "⚖️ **ارزیابی و برآورد قیمت هوشمند آیفون (دانیفون)**\n\n"
        "برای برآورد دقیق قیمت خرید دستگاه شما، لطفاً مراحل زیر را به ترتیب با کلیک روی دکمهها دنبال کنید:\n\n"
        "گام ۱ از ۷: **سری آیفون خود را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_series_keyboard(), parse_mode="Markdown")
    return SELECT_SERIES

def handle_series_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
        
    series_code = data.replace("pricing_series_", "")
    context.user_data['wizard_specs']['series'] = series_code
    
    msg_text = (
        f"⚖️ **ارزیابی قیمت آیفون (سری {series_code})**\n\n"
        "گام ۲ از ۷: **مدل دقیق دستگاه را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_model_keyboard(series_code), parse_mode="Markdown")
    return SELECT_MODEL

def handle_model_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_series":
        return start_pricing_wizard(update, context)
        
    model_name = data.replace("pricing_model_", "")
    context.user_data['wizard_specs']['model'] = model_name
    
    msg_text = (
        f"📱 **مدل انتخابی:** {model_name}\n\n"
        "گام ۳ از ۷: **ظرفیت حافظه دستگاه را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_storage_keyboard(), parse_mode="Markdown")
    return SELECT_STORAGE

def handle_storage_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_model":
        series_code = context.user_data.get('wizard_specs', {}).get('series', '15')
        msg_text = f"⚖️ **ارزیابی قیمت آیفون (سری {series_code})**\n\nگام ۲ از ۷: **مدل دقیق دستگاه را انتخاب کنید:**"
        query.edit_message_text(msg_text, reply_markup=_build_model_keyboard(series_code), parse_mode="Markdown")
        return SELECT_MODEL
        
    cap_val = data.replace("pricing_cap_", "")
    context.user_data['wizard_specs']['capacity'] = cap_val
    model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
    
    msg_text = (
        f"📱 **مدل:** {model_name} ({cap_val}GB)\n\n"
        "گام ۴ از ۷: **سلامت باتری دستگاه را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_battery_keyboard(), parse_mode="Markdown")
    return SELECT_BATTERY

def handle_battery_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_storage":
        model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
        msg_text = f"📱 **مدل انتخابی:** {model_name}\n\nگام ۳ از ۷: **ظرفیت حافظه دستگاه را انتخاب کنید:**"
        query.edit_message_text(msg_text, reply_markup=_build_storage_keyboard(), parse_mode="Markdown")
        return SELECT_STORAGE
        
    bat_type = data.replace("pricing_bat_", "")
    if bat_type == "100":
        bat_val = 100
        bat_label = "۱۰۰٪ فابریک"
    elif bat_type == "95":
        bat_val = 95
        bat_label = "۹۰٪ تا ۹۹٪"
    elif bat_type == "85":
        bat_val = 85
        bat_label = "۸۰٪ تا ۸۹٪"
    elif bat_type == "75":
        bat_val = 75
        bat_label = "زیر ۸۰٪ (نیاز به تعویض)"
    else:  # replaced
        bat_val = 85
        bat_label = "باتری تعویضی (۱۰۰٪ تعویض)"

    context.user_data['wizard_specs']['battery'] = bat_val
    context.user_data['wizard_specs']['battery_label'] = bat_label
    
    model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
    cap_val = context.user_data['wizard_specs'].get('capacity', '128')
    
    msg_text = (
        f"📱 **دستگاه:** {model_name} ({cap_val}GB)\n"
        f"🔋 **باتری:** {bat_label}\n\n"
        "گام ۵ از ۷: **وضعیت رجیستری دستگاه را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_registry_keyboard(), parse_mode="Markdown")
    return SELECT_REGISTRY

def handle_registry_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_battery":
        model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
        cap_val = context.user_data['wizard_specs'].get('capacity', '128')
        msg_text = f"📱 **مدل:** {model_name} ({cap_val}GB)\n\nگام ۴ از ۷: **سلامت باتری دستگاه را انتخاب کنید:**"
        query.edit_message_text(msg_text, reply_markup=_build_battery_keyboard(), parse_mode="Markdown")
        return SELECT_BATTERY
        
    reg_val = data.replace("pricing_reg_", "")
    context.user_data['wizard_specs']['register'] = reg_val
    
    reg_label = "کددار (با رجیستر رسمی)" if reg_val == "Registered" else ("مصوبه کد ملی" if reg_val == "NationalID" else "بدون کد (بدون رجیستر)")
    context.user_data['wizard_specs']['reg_label'] = reg_label

    model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
    cap_val = context.user_data['wizard_specs'].get('capacity', '128')
    
    msg_text = (
        f"📱 **دستگاه:** {model_name} ({cap_val}GB)\n"
        f"🟢 **رجیستری:** {reg_label}\n\n"
        "گام ۶ از ۷: **پارتنامبر و سیمکارت را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_part_keyboard(), parse_mode="Markdown")
    return SELECT_PART

def handle_part_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_registry":
        model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
        cap_val = context.user_data['wizard_specs'].get('capacity', '128')
        msg_text = f"📱 **دستگاه:** {model_name} ({cap_val}GB)\n\nگام ۵ از ۷: **وضعیت رجیستری دستگاه را انتخاب کنید:**"
        query.edit_message_text(msg_text, reply_markup=_build_registry_keyboard(), parse_mode="Markdown")
        return SELECT_REGISTRY
        
    part_val = data.replace("pricing_part_", "")
    context.user_data['wizard_specs']['part'] = part_val
    sim_val = "دو سیمکارت" if part_val in ["ZA/A", "CH/A"] else ("تک سیمکارت" if part_val == "LL/A" else "نامشخص")
    context.user_data['wizard_specs']['sim'] = sim_val

    model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
    cap_val = context.user_data['wizard_specs'].get('capacity', '128')
    
    msg_text = (
        f"📱 **دستگاه:** {model_name} ({cap_val}GB)\n"
        f"📌 **پارت:** {part_val} ({sim_val})\n\n"
        "گام ۷ از ۷: **وضعیت ظاهری و تعویض قطعات را انتخاب کنید:**"
    )
    query.edit_message_text(msg_text, reply_markup=_build_condition_keyboard(), parse_mode="Markdown")
    return SELECT_CONDITION

def handle_condition_step(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "pricing_cancel":
        return cancel_pricing_wizard(update, context)
    if data == "pricing_back_to_part":
        model_name = context.user_data['wizard_specs'].get('model', 'iPhone')
        cap_val = context.user_data['wizard_specs'].get('capacity', '128')
        msg_text = f"📱 **دستگاه:** {model_name} ({cap_val}GB)\n\nگام ۶ از ۷: **پارتنامبر و سیمکارت را انتخاب کنید:**"
        query.edit_message_text(msg_text, reply_markup=_build_part_keyboard(), parse_mode="Markdown")
        return SELECT_PART

    cond_key = data.replace("pricing_cond_", "")
    if cond_key == "BackGlass":
        cond_label = "درب پشت تعویض"
    elif cond_key == "LCD":
        cond_label = "ال سی دی تعویض"
    elif cond_key == "Repaired":
        cond_label = "تعویضی / خط و خش"
    else:
        cond_label = "Clean"

    specs = context.user_data.get('wizard_specs', {})
    specs['condition'] = cond_label
    user = update.effective_user

    # Calculate valuation using expert engine
    model = specs.get('model', 'iPhone 15 Pro')
    capacity = specs.get('capacity', '128')
    battery = int(specs.get('battery', 85))
    register = specs.get('register', 'Registered')
    part = specs.get('part', 'ZA/A')
    sim = specs.get('sim', 'دو سیمکارت')

    calc_res = pricing_service.calculate_price(
        model=model,
        capacity=capacity,
        battery=battery,
        register=register,
        condition=cond_label
    )

    if not calc_res.get("success"):
        error_msg = calc_res.get("error", "متاسفانه برآورد قیمت امکانپذیر نبود.")
        retry_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 برآورد قیمت جدید", callback_data="menu_pricing")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ])
        query.edit_message_text(error_msg, reply_markup=retry_kb, parse_mode="HTML")
        return ConversationHandler.END

    buy_price = int(calc_res.get("buy_price", 0))
    sell_price = int(calc_res.get("sell_price", 0))
    buy_fmt = pricing_service._fmt(buy_price)
    sell_fmt = pricing_service._fmt(sell_price)
    buy_range_str = calc_res.get("buy_range_str") or f"{buy_fmt} تومان"

    reg_str = "بدون رجیستر (بدون کد)" if register == "Unregistered" else ("مصوبه کد ملی" if register == "NationalID" else "کددار (با رجیستر)")
    bat_str = f"{battery}%"

    # Invoke Gemini AI Agent to generate reasoned expert evaluation
    try:
        ai_quote = ai_engine.generate_expert_quote(specs)
        if ai_quote and len(ai_quote) > 30 and not any(err in ai_quote for err in ["HTTP 429", "HTTP 400"]):
            quote_text = ai_quote
        else:
            quote_text = (
                f"📱 **فاکتور برآورد قیمت هوشمند دانیفون**\n\n"
                f"▫️ **مدل دستگاه:** {model} ({capacity}GB)\n"
                f"▫️ **سلامت باتری:** {bat_str}\n"
                f"▫️ **وضعیت رجیستری:** {reg_str}\n"
                f"▫️ **پارتنامبر:** {part} ({sim})\n"
                f"▫️ **وضعیت ظاهری:** {cond_label if cond_label != 'Clean' else 'تمیز و سالم (Clean)'}\n\n"
                f"💰 **حدود قیمت تخمینی خرید ما از شما:** {buy_range_str}\n"
                f"🏷️ **قیمت پایه بازار:** {sell_fmt} تومان\n\n"
                f"📌 *توضیحات:* قیمتگذاری بر اساس الگوریتم هوشمند دیتابیس خریدهای واقعی دانیفون انجام شده است.\n"
                f"📞 جهت تایید نهایی معامله و هماهنگی با کارشناس تماس بگیرید: @{config.EXPERT_USERNAME}"
            )
    except Exception as ai_err:
        logger.warning(f"Failed to generate AI quote text: {ai_err}")
        quote_text = (
            f"📱 **فاکتور برآورد قیمت هوشمند دانیفون**\n\n"
            f"▫️ **مدل دستگاه:** {model} ({capacity}GB)\n"
            f"▫️ **سلامت باتری:** {bat_str}\n"
            f"▫️ **وضعیت رجیستری:** {reg_str}\n"
            f"▫️ **پارتنامبر:** {part} ({sim})\n"
            f"▫️ **وضعیت ظاهری:** {cond_label if cond_label != 'Clean' else 'تمیز و سالم (Clean)'}\n\n"
            f"💰 **حدود قیمت تخمینی خرید ما از شما:** {buy_range_str}\n"
            f"🏷️ **قیمت پایه بازار:** {sell_fmt} تومان\n\n"
            f"📌 *توضیحات:* قیمتگذاری بر اساس الگوریتم هوشمند دیتابیس خریدهای واقعی دانیفون انجام شده است.\n"
            f"📞 جهت تایید نهایی معامله و هماهنگی با کارشناس تماس بگیرید: @{config.EXPERT_USERNAME}"
        )

    action_id = str(uuid.uuid4())[:8]

    # Save pricing request to database
    raw_summary_text = f"{model} {capacity}GB bat:{battery}% reg:{register} part:{part} cond:{cond_label}"
    quote_payload = {
        "model": model,
        "capacity": capacity,
        "battery": battery,
        "register": register,
        "color": "نامشخص",
        "part": part,
        "sim": sim,
        "condition": cond_label,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "buy_range_str": buy_range_str,
        "quote_text": quote_text
    }

    try:
        database.save_pricing_request(
            request_id=action_id,
            user_id=user.id,
            user_full_name=user.full_name,
            username=user.username or "",
            user_specs_raw=raw_summary_text,
            quote_json=json.dumps(quote_payload, ensure_ascii=False)
        )
    except Exception as e:
        logger.error(f"Failed to save wizard pricing request to DB: {e}")

    if 'approval_requests' not in context.bot_data:
        context.bot_data['approval_requests'] = {}
    context.bot_data['approval_requests'][action_id] = {
        'user_id': user.id,
        'draft_text': quote_text,
        'quote': quote_payload
    }

    # Inform customer that request is registered and pending admin approval
    customer_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 کانال تلگرام دانیفون", url="https://t.me/daniphoneir")],
        [InlineKeyboardButton(f"📞 ارتباط با کارشناس (@{config.EXPERT_USERNAME})", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ])

    customer_msg = (
        "✅ **مشخصات دستگاه شما با موفقیت دریافت شد.**\n\n"
        f"▫️ **دستگاه:** {model} ({capacity}GB)\n"
        f"▫️ **سلامت باتری:** {bat_str}\n"
        f"▫️ **وضعیت رجیستری:** {reg_str}\n"
        f"▫️ **پارتنامبر:** {part} ({sim})\n"
        f"▫️ **وضعیت ظاهری:** {cond_label if cond_label != 'Clean' else 'تمیز و سالم (Clean)'}\n\n"
        "⏳ مشخصات دستگاه جهت برآورد قیمت و تایید نهایی برای کارشناس ارشد دانیفون ارسال گردید.\n"
        "پس از بررسی و تایید کارشناس، نتیجه نهایی به همین پیام برای شما ارسال خواهد شد."
    )
    query.edit_message_text(customer_msg, reply_markup=customer_keyboard, parse_mode="Markdown")

    # Forward to Admin targets for approval
    try:
        admin_targets = []
        if config.ADMIN_CHAT_ID and config.ADMIN_CHAT_ID != -5544060808:
            admin_targets.append(config.ADMIN_CHAT_ID)
        for admin_id in config.AUTHORIZED_ADMINS:
            if admin_id not in admin_targets:
                admin_targets.append(admin_id)

        safe_name = utils.escape_markdown(user.full_name)
        safe_username = utils.escape_markdown(user.username) if user.username else 'ندارد'
        admin_msg = (
            "📩 **درخواست جدید کارشناسی و قیمتگذاری آیفون (ویزارد)**\n\n"
            f"👤 **مشتری:** {safe_name}\n"
            f"🆔 **شناسه تلگرام:** `{user.id}`\n"
            f"📎 **آیدی:** @{safe_username}\n\n"
            f"📱 **مدل:** {model} ({capacity}GB)\n"
            f"🔋 **باتری:** {bat_str} | 🟢 **رجیستری:** {reg_str}\n"
            f"📌 **پارت:** {part} ({sim}) | 🎨 **ظاهر:** {cond_label}\n\n"
            f"🤖 **قیمت برآوردی الگوریتم:** {calc_res.get('buy_range_str', buy_fmt + ' تومان')}"
        )
        approval_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✅ تایید ({calc_res.get('buy_range_str', buy_fmt + ' تومان')})", callback_data=f"approve_{action_id}_{user.id}"),
                InlineKeyboardButton("✏️ ویرایش قیمت / رد", callback_data=f"modify_{action_id}_{user.id}")
            ]
        ])

        for admin_target in admin_targets:
            try:
                utils.send_chunked_message(
                    context.bot,
                    chat_id=admin_target,
                    text=admin_msg,
                    reply_markup=approval_keyboard,
                    parse_mode="Markdown"
                )
            except Exception as admin_err:
                logger.warning(f"Could not send pricing notification to admin target {admin_target}: {admin_err}")
    except Exception as notify_err:
        logger.error(f"Error notifying admins from wizard: {notify_err}")

    context.user_data.clear()
    return ConversationHandler.END

def cancel_pricing_wizard(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    if query:
        query.answer()
        query.edit_message_text(
            "❌ **فرآیند قیمتگذاری لغو شد.**\n\nمیتوانید هر زمان از منوی اصلی اقدام فرمایید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )
    context.user_data.clear()
    return ConversationHandler.END

# --- ADMIN HITL HANDLERS ---

def start_pricing_flow(update: Update, context: CallbackContext) -> None:
    """Legacy entry wrapper forwarding to wizard."""
    return start_pricing_wizard(update, context)

def handle_ai_price_input(update: Update, context: CallbackContext) -> None:
    """Fallback text handler if user sends free text."""
    return None

def parse_admin_price(admin_input: str, default_price: int = 0) -> int:
    """Parses admin entered price supporting various formats: digits, Persian digits, decimals, 162.5m, etc."""
    if not admin_input:
        return default_price
    
    persian_arabic = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
    english = "01234567890123456789"
    trans = str.maketrans(persian_arabic, english)
    text = admin_input.translate(trans).strip()
    text = text.replace("/", ".")
    
    m_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:میلیون|m)", text, re.IGNORECASE)
    if m_match:
        val = float(m_match.group(1))
        return int(val * 1_000_000)
        
    t_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:تومان|toman)", text, re.IGNORECASE)
    if t_match:
        val = float(t_match.group(1))
        if val < 1000:
            return int(val * 1_000_000)
        return int(val)
        
    digits_only = re.sub(r"[^\d]", "", text)
    if digits_only:
        val = int(digits_only)
        if val < 1000:
            return int(val * 1_000_000)
        return val
        
    return default_price

def extract_expert_reason(admin_input: str) -> str:
    """Extracts textual reason/explanation from admin feedback input by stripping the price digits/units."""
    if not admin_input:
        return ""
    text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:میلیون|m|تومان|toman)", "", admin_input, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{6,10}\b", "", text)
    clean_reason = re.sub(r"^[\s\-:,\.\_\|]+", "", text).strip()
    return clean_reason if len(clean_reason) > 2 else ""

def analyze_price_variance(initial_price: int, corrected_price: int, model: str, expert_reason: str = "") -> dict:
    """Analyzes variance between initial AI/Algorithm quote and expert corrected price for continuous machine learning."""
    diff = corrected_price - initial_price
    if initial_price > 0:
        pct = round((diff / initial_price) * 100, 2)
    else:
        pct = 0.0

    reason_suffix = f" | دلیل و توضیحات کارشناس: «{expert_reason}»" if expert_reason else ""
        
    if diff > 0:
        direction = "UNDERESTIMATED"
        reason = f"برآورد اولیه هوش مصنوعی {abs(diff):,} تومان ({pct}%) پایینتر از نظر کارشناس بود. جهت بهبود برآوردهای بعدی {model}، پایه قیمت/پاداش تعدیل مثبت شود.{reason_suffix}"
    elif diff < 0:
        direction = "OVERESTIMATED"
        reason = f"برآورد اولیه هوش مصنوعی {abs(diff):,} تومان ({abs(pct)}%) بالاتر از نظر کارشناس بود. جهت بهبود برآوردهای بعدی {model}، پایه قیمت/میزان افت تعدیل منفی شود.{reason_suffix}"
    else:
        direction = "MATCHED"
        reason = f"قیمت هوش مصنوعی کاملاً دقیق و تاییدشده توسط کارشناس بود (تطابق ۱۰۰٪).{reason_suffix}"

    return {
        "initial_ai_price": initial_price,
        "corrected_price": corrected_price,
        "difference": diff,
        "variance_pct": pct,
        "direction": direction,
        "expert_reason": expert_reason,
        "analysis_insight": reason
    }

@admin_required
def handle_admin_approval_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data
    
    parts = data.split("_")
    if len(parts) < 3:
        query.edit_message_text("❌ دکمه تایید معتبر نیست.")
        return
        
    action = parts[0]
    action_id = parts[1]
    user_id = int(parts[2])
    
    db_req = database.get_pricing_request(action_id)
    req_store = context.bot_data.get('approval_requests', {})
    req_data = req_store.get(action_id, {})
    
    if db_req:
        quote = json.loads(db_req["quote_json"]) if db_req["quote_json"] else {}
        user_specs_raw = db_req["user_specs_raw"]
    elif req_data:
        quote = req_data.get('quote', {})
        user_specs_raw = req_data.get('draft_text', '')
    else:
        query.edit_message_text("❌ اطلاعات این درخواست در حافظه یافت نشد.")
        return
        
    if action == "approve":
        buy_price = quote.get('buy_price', 0)
        buy_fmt = pricing_service._fmt(buy_price)
        buy_range_str = quote.get('buy_range_str') or pricing_service.format_5m_range(buy_price)[2]
        model_name = quote.get('model', 'آیفون')
        
        database.update_pricing_request(action_id, status="approved", final_price=buy_price)
        
        user_message = quote.get('quote_text') or (
            "✅ **برآورد قیمت دستگاه شما توسط کارشناس ارشد تایید شد.**\n\n"
            f"📱 **دستگاه:** {model_name} ({quote.get('capacity')}GB)\n"
            f"💰 **حدود قیمت تخمینی خرید از شما:** {buy_range_str}\n\n"
            f"📞 جهت نهایی کردن فروش با کارشناس تماس بگیرید: @{config.EXPERT_USERNAME}"
        )
        
        customer_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📞 تماس با کارشناس (@{config.EXPERT_USERNAME})", url=f"https://t.me/{config.EXPERT_USERNAME}")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ])
        
        try:
            analysis = analyze_price_variance(buy_price, buy_price, model_name)
            _save_to_knowledge_base(
                model=model_name,
                capacity=f"{quote.get('capacity')}GB",
                battery=f"{quote.get('battery')}%",
                register=quote.get('register'),
                buy_price=buy_price,
                notes=f"تایید ۱۰۰٪ کارشناس | {analysis['analysis_insight']}"
            )
            feedback_payload = {
                "initial_ai_price": buy_price,
                "corrected_price": buy_price,
                "status": "APPROVED",
                "analysis": analysis,
                "quote": quote
            }
            database.add_feedback(
                agent_action=user_specs_raw,
                admin_response="Approved by Admin",
                corrected_data=json.dumps(feedback_payload, ensure_ascii=False)
            )
        except Exception as e:
            logger.error(f"Failed to record approved quote in KB/Feedback: {e}")

        try:
            utils.send_chunked_message(
                bot=context.bot,
                chat_id=user_id,
                text=user_message,
                reply_markup=customer_keyboard,
                parse_mode="Markdown"
            )
            query.edit_message_text(f"✅ درخواست قیمتگذاری {model_name} با بازه قیمت {buy_range_str} تایید و برای مشتری ارسال شد.")
        except Exception as e:
            logger.error(f"Failed to message approved user {user_id}: {e}")
            err_str = str(e).lower()
            if "blocked" in err_str or "unauthorized" in err_str or "forbidden" in err_str:
                query.edit_message_text("⚠️ تایید شد اما ارسال پیام به کاربر ناموفق بود (احتمال بلاک توسط کاربر).")
            else:
                query.edit_message_text(f"⚠️ تایید شد اما ارسال پیام به کاربر با خطا مواجه شد ({e}).")
            
        req_store.pop(action_id, None)
        return ConversationHandler.END
        
    elif action == "modify":
        context.user_data['feedback_action_id'] = action_id
        context.user_data['feedback_user_id'] = user_id
        query.edit_message_text(
            "✏️ **تصحیح قیمت و آموزش به هوش مصنوعی**\n\n"
            "لطفاً قیمت جدید تاییدشده را به تومان وارد کنید (مثلاً: 162550000 یا 162.5m یا 162/5 میلیون تومان).\n"
            "این قیمت به همراه تحلیل انحراف قیمت قبلی هوش مصنوعی در دیتابیس یادگیری هوش مصنوعی ذخیره میشود:"
        )
        return WAITING_FOR_ADMIN_FEEDBACK
        
    return ConversationHandler.END

def contact_expert(update: Update, context: CallbackContext) -> None:
    """Forward quote details to admin and initiate HITL approval loop."""
    if update.callback_query:
        update.callback_query.answer("درخواست شما با موفقیت برای کارشناس ثبت شد.", show_alert=True)

# Backward compatibility alias
handle_admin_decision = handle_admin_approval_callback

def receive_admin_feedback(update: Update, context: CallbackContext) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END

    admin_input = update.message.text.strip()
    action_id = context.user_data.get('feedback_action_id')
    user_id = context.user_data.get('feedback_user_id')
    
    db_req = database.get_pricing_request(action_id) if action_id else None
    req_store = context.bot_data.get('approval_requests', {})
    memory_req = req_store.get(action_id, {}) if action_id else {}
    
    if db_req:
        quote = json.loads(db_req["quote_json"]) if db_req["quote_json"] else {}
        raw_text = db_req["user_specs_raw"]
    elif memory_req:
        quote = memory_req.get('quote', {})
        raw_text = memory_req.get('draft_text', '')
    else:
        quote = {}
        raw_text = "نامشخص"

    initial_buy = int(quote.get('buy_price', 0))
    model_name = quote.get('model', 'iPhone 15 Pro')
    corrected_buy_price = parse_admin_price(admin_input, default_price=initial_buy)
    corrected_fmt = pricing_service._fmt(corrected_buy_price)
    _, _, corrected_range_str = pricing_service.format_5m_range(corrected_buy_price)
    expert_reason = extract_expert_reason(admin_input)

    # Perform automated AI variance comparison incorporating expert reason
    variance_analysis = analyze_price_variance(initial_buy, corrected_buy_price, model_name, expert_reason=expert_reason)

    try:
        kb_note = (
            f"اصلاح کارشناس: قیمت هوش مصنوعی از {pricing_service._fmt(initial_buy)} به {corrected_fmt} "
            f"تغییر یافت ({variance_analysis['variance_pct']}%) | {variance_analysis['analysis_insight']}"
        )
        _save_to_knowledge_base(
            model=model_name,
            capacity=f"{quote.get('capacity', '256')}GB",
            battery=f"{quote.get('battery', 85)}%",
            register=quote.get('register', 'Registered'),
            buy_price=corrected_buy_price,
            notes=kb_note
        )
        
        feedback_payload = {
            "initial_ai_price": initial_buy,
            "corrected_price": corrected_buy_price,
            "expert_reason": expert_reason,
            "variance": variance_analysis,
            "admin_raw_input": admin_input,
            "specs": quote
        }
        
        database.add_feedback(
            agent_action=raw_text,
            admin_response=admin_input,
            corrected_data=json.dumps(feedback_payload, ensure_ascii=False)
        )
        if action_id:
            database.update_pricing_request(
                action_id,
                status="modified",
                final_price=corrected_buy_price,
                expert_notes=f"Admin: {admin_input} | Reason: {expert_reason} | Learning: {variance_analysis['analysis_insight']}"
            )
    except Exception as e:
        logger.error(f"Failed to log admin feedback & learning analysis: {e}")

    user_msg = (
        "✅ **برآورد قیمت دستگاه شما توسط کارشناس ارشد تایید و بروزرسانی شد.**\n\n"
        f"📱 **دستگاه:** {model_name} ({quote.get('capacity', '256')}GB)\n"
        f"💰 **حدود قیمت تخمینی خرید از شما:** {corrected_range_str}\n\n"
        f"📞 جهت هماهنگی معامله با کارشناس تماس بگیرید: @{config.EXPERT_USERNAME}"
    )
    customer_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📞 تماس با کارشناس (@{config.EXPERT_USERNAME})", url=f"https://t.me/{config.EXPERT_USERNAME}")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    reason_display = f"📝 **دلیل کارشناس:** {expert_reason}\n" if expert_reason else ""
    admin_confirm_msg = (
        "✅ **قیمت اصلی و دلیل اصلاح دریافت شد.**\n\n"
        f"▫️ **قیمت اولیه هوش مصنوعی:** {pricing_service._fmt(initial_buy)} تومان\n"
        f"▫️ **بازه قیمت جدید کارشناس:** {corrected_range_str} (قیمت دقیق دیتابیس: {corrected_fmt} تومان)\n"
        f"📊 **میزان انحراف:** {variance_analysis['variance_pct']}%\n"
        f"{reason_display}"
        f"💡 **نتیجه تحلیل یادگیری:** {variance_analysis['analysis_insight']}\n\n"
        "این دادهها به همراه علت اصلاح در حافظه یادگیری هوش مصنوعی ذخیره شد و بازه قیمت جدید برای مشتری ارسال گردید."
    )
    update.message.reply_text(admin_confirm_msg, parse_mode="Markdown")

    if user_id:
        try:
            utils.send_chunked_message(
                bot=context.bot,
                chat_id=user_id,
                text=user_msg,
                reply_markup=customer_keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to forward feedback to user {user_id}: {e}")
            err_str = str(e).lower()
            if "blocked" in err_str or "unauthorized" in err_str or "forbidden" in err_str:
                update.message.reply_text(f"⚠️ بازه قیمت {corrected_range_str} در دیتابیس ثبت شد اما کاربر ربات را بلاک کرده است.")
            else:
                update.message.reply_text(f"⚠️ بازه قیمت {corrected_range_str} در دیتابیس ثبت شد اما ارسال پیام به کاربر با خطا مواجه شد ({e}).")

    if action_id:
        req_store.pop(action_id, None)
    context.user_data.clear()
    return ConversationHandler.END

def _save_to_knowledge_base(model: str, capacity: str, battery: str, register: str, buy_price: float, notes: str) -> None:
    kb_path = config.KNOWLEDGE_BASE_PATH
    kb_data = []
    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb_data = json.load(f)
        except Exception:
            kb_data = []

    new_record = {
        "model": model,
        "capacity": capacity,
        "battery": battery,
        "register": "دارد" if register == "Registered" else "ندارد",
        "buy_price": buy_price,
        "notes": notes
    }
    kb_data.insert(0, new_record)

    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    with open(kb_path, "w", encoding="utf-8") as f:
        json.dump(kb_data, f, ensure_ascii=False, indent=2)

def cancel_feedback(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()
    update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END
