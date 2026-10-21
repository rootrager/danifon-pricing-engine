import os
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
from core import config, database
from core.security import admin_required
from services import vision_service, marketing_service
from image_matcher import find_best_image

logger = logging.getLogger(__name__)

WAIT_STORY_PHOTO, STORY_FEEDBACK, WAIT_TEXT_POST_SPEC = range(60, 63)

@admin_required
def admin_text_post_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "📱 **ساخت پست کانال با انتخاب عکس اتوماتیک از انبار**\n\n"
        "لطفاً مدل، رنگ و مشخصات دستگاه را تایپ کنید:\n"
        "*(مثلاً: آیفون 16 پرو مکس 256 نچرال تیتانیوم بدون کد باتری 98 - قیمت 172 میلیون)*"
    )
    return WAIT_TEXT_POST_SPEC

@admin_required
def admin_receive_text_post_spec(update: Update, context: CallbackContext) -> int:
    if not update.message or not update.message.text:
        return WAIT_TEXT_POST_SPEC

    spec_text = update.message.text.strip()
    update.message.reply_text("🔄 در حال یافتن تصویر منطبق از کاتالوگ انبار و ساخت پست کانال...")

    try:
        post_data = marketing_service.create_channel_post_from_text_spec(spec_text)
        post_text = post_data["text"]
        image_path = post_data["image_path"]

        draft_id = database.save_story_draft(update.effective_user.id, image_path or "", post_text)
        context.user_data['current_story_draft_id'] = draft_id

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید و انتشار به کانال", callback_data=f"story_publish_{draft_id}")],
            [InlineKeyboardButton("✏️ اصلاح پست", callback_data=f"story_modify_{draft_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data=f"story_cancel_{draft_id}")]
        ])

        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f,
                    caption=f"📝 **پیشنویس پست کانال (با تصویر انبار):**\n\n{post_text}",
                    reply_markup=reply_markup
                )
        else:
            update.message.reply_text(f"📝 **پیشنویس پست کانال:**\n\n{post_text}", reply_markup=reply_markup)

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error creating text channel post: {e}")
        update.message.reply_text(f"❌ خطا در تولید پست: {e}")
        return ConversationHandler.END

@admin_required
def admin_story_start(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text("📸 لطفاً تصویر دستگاه یا استوری را ارسال کنید:")
    return WAIT_STORY_PHOTO

@admin_required
def admin_receive_story_photo(update: Update, context: CallbackContext) -> int:
    if not update.message or not update.message.photo:
        return WAIT_STORY_PHOTO
        
    photo = update.message.photo[-1]
    file_id = photo.file_id
    save_path = os.path.join(config.DOWNLOADS_DIR, f"{file_id}.jpg")
    
    update.message.reply_text("🔄 در حال آنالیز تصویر و تطبیق رنگ...")
    
    try:
        new_file = context.bot.get_file(file_id)
        new_file.download(save_path)
        
        draft_text = vision_service.generate_post_from_image(save_path)
        if draft_text.startswith("⚠️"):
            update.message.reply_text(draft_text)
            return ConversationHandler.END

        draft_id = database.save_story_draft(update.effective_user.id, save_path, draft_text)
        context.user_data['current_story_draft_id'] = draft_id
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید و انتشار", callback_data=f"story_publish_{draft_id}")],
            [InlineKeyboardButton("✏️ اصلاح پست", callback_data=f"story_modify_{draft_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data=f"story_cancel_{draft_id}")]
        ])
        
        update.message.reply_text(f"📝 پیشنویس پست:\n\n{draft_text}", reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in story analysis: {e}")
        update.message.reply_text(f"❌ خطا در آنالیز تصویر: {e}")
        return ConversationHandler.END

@admin_required
def handle_story_callback(update: Update, context: CallbackContext) -> int:
    """Processes story_publish_ID / story_modify_ID / story_cancel_ID callbacks."""
    query = update.callback_query
    query.answer()
    data = query.data

    parts = data.split("_")
    if len(parts) < 3:
        query.edit_message_text("⚠️ دیتای کالبک نامعتبر است.")
        return ConversationHandler.END

    action = parts[1]
    try:
        draft_id = int(parts[2])
    except ValueError:
        query.edit_message_text("⚠️ شناسه پیشنویس نامعتبر است.")
        return ConversationHandler.END

    draft = database.get_story_draft(draft_id)
    if not draft:
        query.edit_message_text("⚠️ پیشنویس یافت نشد.")
        return ConversationHandler.END

    if action == "publish":
        query.edit_message_text("🔄 در حال انتشار به کانال...")
        final_text = draft['current_draft']
        catalog_image = find_best_image(final_text)
        image_path = catalog_image if catalog_image else draft['image_path']

        try:
            success, err_msg = marketing_service.publish_post_detailed(
                chat_id=query.message.chat_id,
                text=final_text,
                image_path=image_path,
                channel_id=config.CHANNEL_ID
            )
            if success:
                database.update_story_draft_status(draft_id, 'published')
                query.edit_message_text("✅ پست با موفقیت در کانال منتشر شد!")
            else:
                query.edit_message_text(f"❌ خطا در انتشار پست به کانال:\n{err_msg}")
        except Exception as e:
            logger.error(f"Failed to publish story post: {e}")
            query.edit_message_text(f"❌ خطا در انتشار: {e}")

    elif action == "modify":
        context.user_data['modifying_story_draft_id'] = draft_id
        query.edit_message_text("✏️ لطفاً تغییری که میخواهید اعمال شود را بنویسید (مثلاً: قیمت را به 165 میلیون تغییر بده):")
        return STORY_FEEDBACK

    elif action == "cancel":
        database.update_story_draft_status(draft_id, 'cancelled')
        query.edit_message_text("❌ عملیات لغو شد.")

    return ConversationHandler.END

@admin_required
def admin_receive_story_feedback(update: Update, context: CallbackContext) -> int:
    draft_id = context.user_data.get('modifying_story_draft_id')
    if not draft_id:
        return ConversationHandler.END

    feedback = update.message.text
    draft = database.get_story_draft(draft_id)
    if not draft:
        context.user_data.pop('modifying_story_draft_id', None)
        update.message.reply_text("⚠️ پیشنویس یافت نشد.")
        return ConversationHandler.END

    update.message.reply_text("🔄 در حال اعمال اصلاحات...")

    try:
        revised = vision_service.revise_post_with_feedback(draft['current_draft'], feedback)
        database.update_story_draft(draft_id, revised)
        database.save_story_feedback(draft_id, update.effective_user.id, feedback)

        context.user_data.pop('modifying_story_draft_id', None)

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید و انتشار", callback_data=f"story_publish_{draft_id}")],
            [InlineKeyboardButton("✏️ اصلاح مجدد", callback_data=f"story_modify_{draft_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data=f"story_cancel_{draft_id}")]
        ])

        update.message.reply_text(f"📝 پیشنویس اصلاحشده:\n\n{revised}", reply_markup=reply_markup)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error revising post draft: {e}")
        update.message.reply_text(f"❌ خطا در اعمال اصلاحات: {e}")
        return ConversationHandler.END
