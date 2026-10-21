import os
import re
import json
import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
)
from core import config, database, utils
from core.security import admin_required
from services import inventory_service, pricing_service, export_service, marketing_service, vision_service

logger = logging.getLogger(__name__)

# State constants
(
    SELECT_ADD_TYPE, SELECT_SERIES, SELECT_MODEL, SELECT_CAPACITY,
    SELECT_PART, SELECT_SIM, SELECT_REGISTRY, SELECT_BATTERY,
    SELECT_PRICE, WAIT_FOR_PHOTO, CONFIRM_PREVIEW
) = range(5, 16)
EDIT_FIELD, EDIT_VALUE = 20, 21
WAIT_BULK_INVENTORY = 70
WAIT_BROADCAST_CONFIRM, WAIT_BROADCAST_CUSTOM_TEXT = 80, 81

SERIES_MODELS = {
    "سری 18": ["iPhone 18", "iPhone 18 Plus", "iPhone 18 Pro", "iPhone 18 Pro Max"],
    "سری 17": ["iPhone 17", "iPhone 17 Plus", "iPhone 17 Pro", "iPhone 17 Pro Max"],
    "سری 16": ["iPhone 16", "iPhone 16 Plus", "iPhone 16 Pro", "iPhone 16 Pro Max"],
    "سری 15": ["iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max"],
    "سری 14": ["iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max"],
    "سری 13": ["iPhone 13", "iPhone 13 Mini", "iPhone 13 Pro", "iPhone 13 Pro Max"],
    "سری 12": ["iPhone 12 mini", "iPhone 12", "iPhone 12 Pro", "iPhone 12 Pro Max"],
    "سری 11": ["iPhone 11", "iPhone 11 Pro", "iPhone 11 Pro Max"],
    "سری X": ["iPhone X", "iPhone XR", "iPhone XS", "iPhone XS Max"],
}

@admin_required
def admin_panel(update: Update, context: CallbackContext) -> None:
    """Send organized admin glass dashboard based on updated architecture."""
    keyboard = [
        [InlineKeyboardButton("📦 آپدیت موجودی آکبند (وبسایت)", callback_data="admin_new_inv_menu")],
        [InlineKeyboardButton("📱 آپدیت موجودی کارکرده (کانال تلگرام)", callback_data="admin_used_inv_menu")],
        [InlineKeyboardButton("🛂 آپدیت لیست ریجستری", callback_data="admin_registry_menu")],
        [InlineKeyboardButton("📢 ارسال پیام به مشتری ها (broadcast)", callback_data="admin_broadcast_start")],
        [InlineKeyboardButton("🚪 خروج دستگاه", callback_data="admin_device_exit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    dashboard_text = (
        "⚙️ **پنل مدیریت هوشمند دانایفون (Admin Dashboard)** ⚙️\n\n"
        "یکی از گزینههای زیر را انتخاب کنید:"
    )
    
    if update.message:
        update.message.reply_text(dashboard_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text(dashboard_text, reply_markup=reply_markup, parse_mode="Markdown")

@admin_required
def admin_new_inv_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ اضافه", callback_data="add_type_new_direct")],
        [InlineKeyboardButton("➖ حذف", callback_data="remove_new_inv")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="return_to_admin_panel")]
    ]
    query.edit_message_text("📦 **آپدیت موجودی آکبند (وبسایت)**\n\nیکی از گزینههای زیر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@admin_required
def admin_used_inv_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ اضافه", callback_data="add_type_used_direct")],
        [InlineKeyboardButton("➖ حذف", callback_data="remove_used_inv")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="return_to_admin_panel")]
    ]
    query.edit_message_text("📱 **آپدیت موجودی کارکرده (کانال تلگرام)**\n\nیکی از گزینههای زیر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@admin_required
def admin_registry_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("ثبت و پاسپورت", callback_data="update_reg_passport")],
        [InlineKeyboardButton("گمرکی", callback_data="update_reg_customs")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="return_to_admin_panel")]
    ]
    query.edit_message_text("🛂 **آپدیت لیست ریجستری**\n\nیکی از گزینههای زیر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

@admin_required
def admin_device_exit(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer("این بخش برای حسابداری است و بعداً فعال میشود.", show_alert=True)

@admin_required
def admin_reg_stub(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer("بخش آپدیت ریجستری به زودی تکمیل میشود.", show_alert=True)


@admin_required
def return_to_admin_panel(update: Update, context: CallbackContext) -> None:
    admin_panel(update, context)

@admin_required
def admin_list_users(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT User_ID, Username, First_Name, Phone_Number, Date_Joined FROM Users ORDER BY Date_Joined DESC")
        rows = cursor.fetchall()
        
        if not rows:
            text = "👥 **لیست مشتریان:**\n\nهنوز هیچ مشتری شماره خود را ثبت نکرده است."
        else:
            lines = ["👥 **لیست شماره مشتریهای ثبت شده در ربات:**\n"]
            for idx, r in enumerate(rows, start=1):
                uid, uname, fname, phone, joined = r
                uname_str = f"@{uname}" if uname else "بدون آیدی"
                lines.append(f"{idx}. **{fname}** ({uname_str})")
                lines.append(f"   📞 شماره: `{phone}`")
                lines.append(f"   🗓 تاریخ ورود: {joined}\n")
            text = "\n".join(lines)
            
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی به این مشتریان", callback_data="admin_broadcast_start")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="return_to_admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        utils.send_chunked_message(
            context.bot,
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error fetching user list: {e}")
        query.edit_message_text("❌ خطا در دریافت لیست مشتریان.")
    finally:
        conn.close()

# --- Bulk Daily Inventory Update Flow (Photo & Text Supported) ---
@admin_required
def admin_bulk_inventory_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "📸 **آپدیت روزانه موجودی انبار با عکس** 📸\n\n"
        "لطفاً **تصویر (عکس لیست قیمت، کاغذ، دفترچه یا تخته)** موجودی روزانه را ارسال کنید.\n"
        "هوش مصنوعی تصویر شما را آنالیز کرده، تمام آیتمها و قیمتها را استخراج میکند و موجودی ربات را بروزرسانی مینماید.\n\n"
        "*(همچنین میتوانید متن لیست را مستقیماً ارسال کنید)*"
    )
    return WAIT_BULK_INVENTORY

@admin_required
def admin_receive_bulk_inventory(update: Update, context: CallbackContext) -> int:
    msg = update.message
    if not msg:
        return WAIT_BULK_INVENTORY

    raw_text = ""
    
    if msg.photo:
        msg.reply_text("🔄 در حال دریافت عکس و آنالیز هوشمند لیست موجودی با Vision LLM...")
        try:
            photo = msg.photo[-1]
            file_id = photo.file_id
            save_path = os.path.join(config.DOWNLOADS_DIR, f"bulk_inv_{file_id}.jpg")
            new_file = context.bot.get_file(file_id)
            new_file.download(save_path)
            
            raw_text = vision_service.extract_inventory_text_from_photo(save_path)
            if not raw_text:
                msg.reply_text("⚠️ متاسفانه متنی از تصویر استخراج نشد. لطفاً عکس واضح تری ارسال کنید یا متن آن را تایپ کنید.")
                return ConversationHandler.END
            msg.reply_text(f"📝 **متن استخراجشده از عکس:**\n\n<pre>{raw_text}</pre>\n\n🔄 در حال ثبت آیتمها در دیتابیس...", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error processing inventory photo: {e}")
            msg.reply_text(f"❌ خطا در پردازش تصویر: {e}")
            return ConversationHandler.END
    elif msg.text:
        raw_text = msg.text.strip()
        msg.reply_text("🔄 در حال پردازش متنی و بروزرسانی موجودی انبار...")

    if not raw_text:
        return WAIT_BULK_INVENTORY

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    parsed_count = 0

    for line in lines:
        try:
            line_clean = re.sub(r"[,\s]", "", line)
            price_match = re.search(r"(\d{7,10})", line_clean)
            if price_match:
                price_val = price_match.group(1)
                item_id = f"item_{parsed_count+1}"
                inventory_service.add_storefront_item(
                    item_id=item_id,
                    item_type="used" if "کارکرده" in line or "باتری" in line or "battery" in line.lower() else "new",
                    series="سری آیفون",
                    model=line.split()[0] if line.split() else "iPhone",
                    capacity="256",
                    part="ZA",
                    sim="دو سیم",
                    registry="Registered",
                    battery="95",
                    price=price_val,
                    condition="Clean",
                    photo_id=""
                )
                parsed_count += 1
        except Exception as e:
            logger.warning(f"Failed to parse line '{line}': {e}")

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="return_to_admin_panel")]
    ])
    
    msg.reply_text(
        f"✅ تعداد {parsed_count} دستگاه از لیست موجودی عکس/متن پردازش و در انبار ثبت گردید.\n"
        "اطلاعات موجودی جهت قیمتگذاری و تولید محتوا بروز شد.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

@admin_required
def generate_channel_post(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    new_grouped, used_grouped = {}, {}
    db = inventory_service.get_storefront_inventory()
    
    for item in db['new'].values():
        new_grouped.setdefault(item["model"], []).append(item)
    for item in db['used'].values():
        used_grouped.setdefault(item["model"], []).append(item)
        
    lines = ["🔥 لیست موجودی روزانه فروشگاه دانیفون 🔥\n"]
    if new_grouped:
        lines.append("🆕 موجودی آکبند:")
        for model, items in new_grouped.items():
            lines.append(f"📱 {model}:")
            for item in items:
                lines.append(f"▫️ ظرفیت: {item.get('capacity', 'نامشخص')} | پارت: {item.get('part', 'نامشخص')} | قیمت: {item.get('price', 'نامشخص')}")
            lines.append("")
        lines.append("------------------\n")
        
    if used_grouped:
        lines.append("🔄 موجودی کارکرده:")
        for model, items in used_grouped.items():
            lines.append(f"📱 {model}:")
            for item in items:
                lines.append(f"▫️ ظرفیت: {item.get('capacity', 'نامشخص')} | باتری: {item.get('battery', 'نامشخص')}% | قیمت: {item.get('price', 'نامشخص')}")
            lines.append("")
            
    lines.append("🆔 ثبت سفارش و مشاوره: @" + config.EXPERT_USERNAME)
    lines.append("📢 کانال تلگرام: https://t.me/daniphoneir")
                
    post_text = "\n".join(lines).strip()
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="return_to_admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"📝 متن لیست موجودی آماده کپی:\n\n<pre>{post_text}</pre>", reply_markup=reply_markup, parse_mode="HTML")

# --- Manual Add Single Item Flow ---
@admin_required
def admin_start_add(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🆕 آکبند", callback_data="add_type_new")],
        [InlineKeyboardButton("🔄 کارکرده", callback_data="add_type_used")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("لطفاً نوع دستگاه را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_ADD_TYPE

@admin_required
def admin_add_new_direct(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['add_item_type'] = 'new'
    keyboard = []
    
    for series in sorted(SERIES_MODELS.keys(), reverse=True):
        keyboard.append([InlineKeyboardButton(series, callback_data=f"add_series_{series}")])
        
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel_add_item")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📱 **اضافه کردن دستگاه آکبند**\n\nسری دستگاه را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_SERIES

@admin_required
def admin_add_used_direct(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['add_item_type'] = 'used'
    keyboard = []
    
    for series in sorted(SERIES_MODELS.keys(), reverse=True):
        keyboard.append([InlineKeyboardButton(series, callback_data=f"add_series_{series}")])
        
    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel_add_item")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📱 **اضافه کردن دستگاه کارکرده**\n\nسری دستگاه را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_SERIES

@admin_required
def admin_select_type(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    item_type = query.data.replace("add_type_", "")
    context.user_data['add_item_type'] = item_type
    
    keyboard = []
    for s_name in SERIES_MODELS.keys():
        keyboard.append([InlineKeyboardButton(s_name, callback_data=f"add_series_{s_name}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("لطفاً سری آیفون را انتخاب کنید:", reply_markup=reply_markup)
    return SELECT_SERIES

@admin_required
def admin_select_series(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    series_name = query.data.replace("add_series_", "")
    context.user_data['add_series'] = series_name
    models = SERIES_MODELS.get(series_name, [])
    
    keyboard = []
    for m in models:
        keyboard.append([InlineKeyboardButton(m, callback_data=f"add_model_{m}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"مدلهای {series_name}:", reply_markup=reply_markup)
    return SELECT_MODEL

@admin_required
def admin_select_model(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    model_name = query.data.replace("add_model_", "")
    context.user_data['add_model'] = model_name
    
    capacities = ["128GB", "256GB", "512GB", "1TB"]
    keyboard = []
    for c in capacities:
        keyboard.append([InlineKeyboardButton(c, callback_data=f"add_cap_{c}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("ظرفیت دستگاه:", reply_markup=reply_markup)
    return SELECT_CAPACITY

@admin_required
def admin_select_capacity(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    cap = query.data.replace("add_cap_", "")
    context.user_data['add_capacity'] = cap
    
    parts = ["ZA", "CH", "LL/A", "LA", "TH"]
    keyboard = []
    for p in parts:
        keyboard.append([InlineKeyboardButton(p, callback_data=f"add_part_{p}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("پارت نامبر دستگاه:", reply_markup=reply_markup)
    return SELECT_PART

@admin_required
def admin_select_part(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    part = query.data.replace("add_part_", "")
    context.user_data['add_part'] = part
    
    keyboard = [
        [InlineKeyboardButton("دو سیمکارت", callback_data="add_sim_دو سیم")],
        [InlineKeyboardButton("تک سیمکارت", callback_data="add_sim_تک سیم")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("تعداد سیمکارت:", reply_markup=reply_markup)
    return SELECT_SIM

@admin_required
def admin_select_sim(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    sim = query.data.replace("add_sim_", "")
    context.user_data['add_sim'] = sim
    
    keyboard = [
        [InlineKeyboardButton("رجیستر شده (کددار)", callback_data="add_reg_Registered")],
        [InlineKeyboardButton("بدون رجیستر (بدون کد)", callback_data="add_reg_Unregistered")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("وضعیت رجیستری:", reply_markup=reply_markup)
    return SELECT_REGISTRY

@admin_required
def admin_select_registry(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    reg = query.data.replace("add_reg_", "")
    context.user_data['add_registry'] = reg
    
    query.edit_message_text("لطفاً درصد سلامت باتری را وارد کنید (مثلاً 95):")
    return SELECT_BATTERY

@admin_required
def receive_battery(update: Update, context: CallbackContext) -> int:
    battery_text = update.message.text.strip()
    context.user_data['add_battery'] = battery_text
    
    update.message.reply_text("لطفاً قیمت فروش به تومان را وارد کنید (مثلاً 185000000):")
    return SELECT_PRICE

@admin_required
def receive_price(update: Update, context: CallbackContext) -> int:
    price_text = update.message.text.strip()
    context.user_data['add_price'] = price_text
    
    ud = context.user_data
    preview_text = (
        "📋 **پیشنمایش آیتم جدید:**\n\n"
        f"نوع: {ud.get('add_item_type')}\n"
        f"مدل: {ud.get('add_model')}\n"
        f"ظرفیت: {ud.get('add_capacity')}\n"
        f"پارت: {ud.get('add_part')}\n"
        f"سیم: {ud.get('add_sim')}\n"
        f"رجیستری: {ud.get('add_registry')}\n"
        f"باتری: {ud.get('add_battery')}%\n"
        f"قیمت: {ud.get('add_price')} تومان"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ تایید و افزودن به انبار", callback_data="confirm_add_item")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_add_item")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRM_PREVIEW

@admin_required
def admin_confirm_preview(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "confirm_add_item":
        ud = context.user_data
        item_id = f"item_{os.urandom(4).hex()}"
        item_type = ud.get('add_item_type', 'used')
        
        inventory_service.add_storefront_item(
            item_id=item_id,
            item_type=item_type,
            series=ud.get('add_series', ''),
            model=ud.get('add_model', ''),
            capacity=ud.get('add_capacity', ''),
            part=ud.get('add_part', ''),
            sim=ud.get('add_sim', ''),
            registry=ud.get('add_registry', ''),
            battery=ud.get('add_battery', ''),
            price=ud.get('add_price', ''),
            condition='کارکرده' if item_type == 'used' else 'آکبند',
            photo_id=''
        )
        
        if item_type == 'used':
            post_text = marketing_service.format_danifon_channel_post(
                model=ud.get('add_model', ''),
                condition='کارکرده',
                color='نامشخص', 
                capacity=ud.get('add_capacity', ''),
                part=ud.get('add_part', ''),
                sim=ud.get('add_sim', ''),
                registry=ud.get('add_registry', ''),
                battery=ud.get('add_battery', ''),
                price=ud.get('add_price', '')
            )
            success = marketing_service.publish_post(None, text=post_text)
            if success:
                query.edit_message_text("✅ دستگاه با موفقیت به انبار کارکرده اضافه شد و پست حرفعای آن در کانال تلگرام درج شد!")
            else:
                query.edit_message_text("✅ دستگاه ذخیره شد اما ارسال پست به کانال تلگرام با خطا مواجه شد. میتوانید دستی فوروارد کنید:\n\n" + post_text)
        else:
            query.edit_message_text("✅ آیتم با موفقیت به موجودی آکبند وبسایت اضافه شد!")
    else:
        query.edit_message_text("❌ عملیات لغو شد.")
        
    context.user_data.clear()
    return ConversationHandler.END

# --- Remove & Edit Item Lists ---
@admin_required
def admin_show_remove_list(update: Update, context: CallbackContext, filter_type=None) -> None:
    query = update.callback_query
    query.answer()
    
    db = inventory_service.get_storefront_inventory()
    keyboard = []
    
    types_to_show = [filter_type] if filter_type else ['new', 'used']
    
    for item_type in types_to_show:
        for item_id, item in db.get(item_type, {}).items():
            btn_text = f"❌ {item['model']} {item['capacity']} ({item.get('price', '')} تومان)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"delete_item_{item_id}")])
            
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="return_to_admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("دستگاههای موجود را جهت حذف انتخاب کنید:", reply_markup=reply_markup)

@admin_required
def admin_remove_new_inv(update: Update, context: CallbackContext) -> None:
    admin_show_remove_list(update, context, filter_type='new')

@admin_required
def admin_remove_used_inv(update: Update, context: CallbackContext) -> None:
    admin_show_remove_list(update, context, filter_type='used')

@admin_required
def admin_execute_removal(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    item_id = query.data.replace("delete_item_", "")
    inventory_service.remove_storefront_item(item_id)
    query.edit_message_text("✅ دستگاه با موفقیت از موجودی انبار حذف شد.")

@admin_required
def admin_show_edit_list(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    db = inventory_service.get_storefront_inventory()
    keyboard = []
    
    for item_type in ['new', 'used']:
        for item_id, item in db[item_type].items():
            btn_text = f"✏️ {item['model']} {item['capacity']} ({item['price']} تومان)"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"edit_select_{item_id}")])
            
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="return_to_admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("دستگاه مورد نظر جهت ویرایش را انتخاب کنید:", reply_markup=reply_markup)

@admin_required
def admin_edit_select(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    item_id = query.data.replace("edit_select_", "")
    context.user_data['editing_item_id'] = item_id
    
    keyboard = [
        [InlineKeyboardButton("ویرایش قیمت", callback_data="edit_field_price")],
        [InlineKeyboardButton("ویرایش باتری", callback_data="edit_field_battery")],
        [InlineKeyboardButton("لغو ویرایش", callback_data="cancel_edit_item")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("کدام فیلد را میخواهید ویرایش کنید؟", reply_markup=reply_markup)
    return EDIT_FIELD

@admin_required
def admin_edit_field(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel_edit_item":
        query.edit_message_text("❌ ویرایش لغو شد.")
        context.user_data.clear()
        return ConversationHandler.END
        
    field = query.data.replace("edit_field_", "")
    context.user_data['editing_field'] = field
    
    query.edit_message_text(f"مقدار جدید برای فیلد {field} را وارد کنید:")
    return EDIT_VALUE

@admin_required
def admin_receive_edit_text(update: Update, context: CallbackContext) -> int:
    new_val = update.message.text.strip()
    item_id = context.user_data.get('editing_item_id')
    field = context.user_data.get('editing_field')
    
    if item_id and field:
        inventory_service.update_storefront_field(item_id, field, new_val)
        update.message.reply_text(f"✅ فیلد {field} با موفقیت به {new_val} تغییر یافت.")
    else:
        update.message.reply_text("❌ خطا در فرآیند ویرایش.")
        
    context.user_data.clear()
    return ConversationHandler.END

@admin_required
def admin_receive_edit_inline(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data.clear()
    query.edit_message_text("✅ ویرایش انجام شد.")
    return ConversationHandler.END

@admin_required
def admin_broadcast_start(update: Update, context: CallbackContext) -> int:
    """Entry point for broadast functionality from admin panel."""
    query = update.callback_query
    if query:
        query.answer()
    
    users = marketing_service.get_broadcast_users()
    total_users = len(users)
    
    default_text = marketing_service.DEFAULT_BROADCAST_TEMPLATE.format(name="[نام مشتری]")
    
    preview_msg = (
        f"📢 **پنل ارسال پیام همگانی (Broadcast)** 📢\n\n"
        f"👥 تعداد گیرندگان فعلی: **{total_users} نفر**\n\n"
        f"📝 **پیشنمایش پیام پیشفرض (ارسال از طرف دانیال):**\n"
        f"──────────────\n"
        f"{default_text}\n"
        f"──────────────\n\n"
        f"آیا مایل به ارسال پیام پیشفرض فوق هستید یا میخواهید متن دلخواه وارد کنید؟"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ ارسال پیام پیشفرض دانیال", callback_data="broadcast_confirm_default")],
        [InlineKeyboardButton("✏️ نوشتن متن اختصاصی جدید", callback_data="broadcast_write_custom")],
        [InlineKeyboardButton("❌ لغو و بازگشت", callback_data="cancel_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        query.edit_message_text(preview_msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        update.message.reply_text(preview_msg, reply_markup=reply_markup, parse_mode="Markdown")
        
    return WAIT_BROADCAST_CONFIRM

@admin_required
def admin_broadcast_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    choice = query.data
    
    if choice == "cancel_broadcast":
        query.edit_message_text("❌ ارسال پیام همگانی لغو شد.")
        context.user_data.clear()
        return ConversationHandler.END
        
    elif choice == "broadcast_confirm_default":
        template = marketing_service.DEFAULT_BROADCAST_TEMPLATE
        query.edit_message_text("🚀 ارسال پیام همگانی در پسزمینه آغاز شد...\nگزارش نهایی پس از اتمام ارسال برای شما ارسال خواهد شد.")
        import threading
        threading.Thread(
            target=marketing_service.execute_broadcast_job,
            args=(context.bot, query.message.chat_id, template),
            daemon=True
        ).start()
        context.user_data.clear()
        return ConversationHandler.END
        
    elif choice == "broadcast_write_custom":
        query.edit_message_text(
            "✍️ **متن اختصاصی خود را جهت ارسال همگانی وارد کنید:**\n\n"
            "نکته: میتوانید از عبارت `{name}` در متن استفاده کنید تا نام هر کاربر به صورت هوشمند جایگزین شود.\n"
            "مثال: `سلام {name} عزیز، ...`\n\n"
            "*(برای لغو دستور /cancel را ارسال کنید)*",
            parse_mode="Markdown"
        )
        return WAIT_BROADCAST_CUSTOM_TEXT

    return WAIT_BROADCAST_CONFIRM

@admin_required
def admin_receive_custom_broadcast(update: Update, context: CallbackContext) -> int:
    custom_text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    update.message.reply_text("🚀 ارسال متن اختصاصی همگانی در پسزمینه آغاز شد...\nگزارش نهایی پس از اتمام ارسال برای شما ارسال خواهد شد.")
    
    import threading
    threading.Thread(
        target=marketing_service.execute_broadcast_job,
        args=(context.bot, chat_id, custom_text),
        daemon=True
    ).start()
    
    context.user_data.clear()
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()
    if update.message:
        update.message.reply_text("❌ عملیات لغو شد.")
    elif update.callback_query:
        update.callback_query.edit_message_text("❌ عملیات لغو شد.")
    return ConversationHandler.END