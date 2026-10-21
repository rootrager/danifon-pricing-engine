# ============================================================
# bot.py — Telegram Bot Logic (Modular & Clean)
# ============================================================
import logging
from telegram import Update
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

# Core imports
from core import config, database, utils, security

# Handlers
from handlers.customer import (
    start,
    show_main_menu,
    handle_contact,
    storefront_menu, # Leaving the old unused logic around temporarily to avoid crashing other imports
    show_used_inventory,
    view_model_item,
    show_new_inventory,
    view_new_model_item,
    show_services_menu,
    start_recommendations_flow,
    receive_budget_input,
    cancel,
    fallback_unknown,
    WAIT_BUDGET_INPUT,
    customer_registry_menu,
    customer_registry_prices,
    customer_apple_id_menu
)

from handlers.pricing import (
    start_pricing_wizard,
    handle_series_step,
    handle_model_step,
    handle_storage_step,
    handle_battery_step,
    handle_registry_step,
    handle_part_step,
    handle_condition_step,
    cancel_pricing_wizard,
    handle_admin_approval_callback,
    handle_admin_decision,
    contact_expert,
    receive_admin_feedback,
    cancel_feedback,
    PRICING_SELECT_SERIES,
    PRICING_SELECT_MODEL,
    PRICING_SELECT_STORAGE,
    PRICING_SELECT_BATTERY,
    PRICING_SELECT_REGISTRY,
    PRICING_SELECT_PART,
    PRICING_SELECT_CONDITION,
    WAITING_FOR_ADMIN_FEEDBACK,
)

from handlers.admin_panel import (
    admin_panel,
    SELECT_ADD_TYPE, SELECT_SERIES, SELECT_MODEL, SELECT_CAPACITY,
    SELECT_PART, SELECT_SIM, SELECT_REGISTRY, SELECT_BATTERY,
    SELECT_PRICE, CONFIRM_PREVIEW, WAIT_BULK_INVENTORY, EDIT_FIELD, EDIT_VALUE,
    WAIT_BROADCAST_CONFIRM, WAIT_BROADCAST_CUSTOM_TEXT, WAIT_FOR_PHOTO,
    return_to_admin_panel,
    SELECT_ADD_TYPE, SELECT_SERIES, SELECT_MODEL, SELECT_CAPACITY,
    SELECT_PART, SELECT_SIM, SELECT_REGISTRY, SELECT_BATTERY,
    SELECT_PRICE, CONFIRM_PREVIEW, WAIT_BULK_INVENTORY, EDIT_FIELD, EDIT_VALUE,
    WAIT_BROADCAST_CONFIRM, WAIT_BROADCAST_CUSTOM_TEXT, WAIT_FOR_PHOTO,
    admin_list_users,
    generate_channel_post,
    admin_bulk_inventory_start,
    admin_receive_bulk_inventory,
    
    admin_new_inv_menu,
    admin_used_inv_menu,
    admin_registry_menu,
    admin_device_exit,
    admin_remove_new_inv,
    admin_remove_used_inv,
    admin_reg_stub,
    
    admin_start_add,
    admin_add_new_direct,
    admin_add_used_direct,
    admin_select_type,
    admin_select_series,
    admin_select_model,
    admin_select_capacity,
    admin_select_part,
    admin_select_sim,
    admin_select_registry,
    receive_battery,
    receive_price,
    admin_confirm_preview,
    admin_show_remove_list,
    admin_execute_removal,
    admin_show_edit_list,
    admin_edit_select,
    admin_edit_field,
    admin_receive_edit_inline,
    admin_receive_edit_text,
    admin_broadcast_start,
    admin_broadcast_choice,
    admin_receive_custom_broadcast,
    cancel
)

from handlers.admin_ai_router import (
    admin_chat_router,
    handle_ai_draft_decision,
)

from handlers.story_pipeline import (
    admin_story_start,
    admin_receive_story_photo,
    admin_text_post_start,
    admin_receive_text_post_spec,
    handle_story_callback,
    admin_receive_story_feedback,
    WAIT_STORY_PHOTO,
    STORY_FEEDBACK,
    WAIT_TEXT_POST_SPEC,
)

logger = logging.getLogger(__name__)

def global_error_handler(update: object, context: CallbackContext) -> None:
    """Log exceptions caused by updates gracefully."""
    logger.error("Exception handling Telegram update %s: %s", update, context.error, exc_info=context.error)

def setup_dispatcher(dispatcher: Dispatcher) -> Dispatcher:
    """
    Register all conversation handlers, commands, callbacks, and message routers.
    """
    # 0. Global Error Handler
    dispatcher.add_error_handler(global_error_handler)

    # 1. Global /start command shows main menu or request contact
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(show_main_menu, pattern='^main_menu$'))
    
    # 2. Storefront menu & inventory navigation
    dispatcher.add_handler(CallbackQueryHandler(show_used_inventory, pattern='^customer_used_inventory$'))
    dispatcher.add_handler(CallbackQueryHandler(view_model_item, pattern='^view_model_'))
    
    # Registry and Apple ID Handlers (New)
    dispatcher.add_handler(CallbackQueryHandler(customer_registry_menu, pattern='^customer_registry$'))
    dispatcher.add_handler(CallbackQueryHandler(customer_registry_prices, pattern='^customer_registry_prices$'))
    dispatcher.add_handler(CallbackQueryHandler(customer_apple_id_menu, pattern='^customer_apple_id$'))

    # 3. Budget / Model Suggestions Conversation
    recommendations_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_recommendations_flow, pattern='^menu_recommendations$')],
        states={
            WAIT_BUDGET_INPUT: [MessageHandler(Filters.text & ~Filters.command, receive_budget_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(recommendations_conv)

    # 4. Admin Panel & Controls
    dispatcher.add_handler(CommandHandler("admin", admin_panel))
    dispatcher.add_handler(CallbackQueryHandler(return_to_admin_panel, pattern='^return_to_admin_panel$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_new_inv_menu, pattern='^admin_new_inv_menu$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_used_inv_menu, pattern='^admin_used_inv_menu$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_registry_menu, pattern='^admin_registry_menu$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_device_exit, pattern='^admin_device_exit$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_reg_stub, pattern='^update_reg_'))
    
    dispatcher.add_handler(CallbackQueryHandler(admin_remove_new_inv, pattern='^remove_new_inv$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_remove_used_inv, pattern='^remove_used_inv$'))

    dispatcher.add_handler(CallbackQueryHandler(generate_channel_post, pattern='^admin_generate_post$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_list_users, pattern='^admin_list_users$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_ai_draft_decision, pattern='^(ai_draft_approve_|ai_draft_reject)'))

    # 4a. Bulk Daily Inventory Update Conversation
    bulk_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_bulk_inventory_start, pattern='^admin_bulk_inventory_start$')],
        states={
            WAIT_BULK_INVENTORY: [
                MessageHandler(Filters.photo, admin_receive_bulk_inventory),
                MessageHandler(Filters.text & ~Filters.command, admin_receive_bulk_inventory)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(bulk_conv)

    # 4b. Admin Manual Add Item Conversation
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_start_add, pattern='^admin_add_item$'),
            CallbackQueryHandler(admin_add_new_direct, pattern='^add_type_new_direct$'),
            CallbackQueryHandler(admin_add_used_direct, pattern='^add_type_used_direct$')
        ],
        states={
            SELECT_ADD_TYPE: [CallbackQueryHandler(admin_select_type, pattern='^add_type_')],
            SELECT_SERIES: [CallbackQueryHandler(admin_select_series, pattern='^add_series_')],
            SELECT_MODEL: [CallbackQueryHandler(admin_select_model, pattern='^add_model_')],
            SELECT_CAPACITY: [CallbackQueryHandler(admin_select_capacity, pattern='^add_cap_')],
            SELECT_PART: [CallbackQueryHandler(admin_select_part, pattern='^add_part_')],
            SELECT_SIM: [CallbackQueryHandler(admin_select_sim, pattern='^add_sim_')],
            SELECT_REGISTRY: [CallbackQueryHandler(admin_select_registry, pattern='^add_reg_')],
            SELECT_BATTERY: [MessageHandler(Filters.text & ~Filters.command, receive_battery)],
            SELECT_PRICE: [MessageHandler(Filters.text & ~Filters.command, receive_price)],
            CONFIRM_PREVIEW: [CallbackQueryHandler(admin_confirm_preview, pattern='^(confirm_add_item|cancel_add_item)$')]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    dispatcher.add_handler(admin_conv_handler)

    # 4c. Admin Edit Item Conversation
    edit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_select, pattern='^edit_select_')],
        states={
            EDIT_FIELD: [CallbackQueryHandler(admin_edit_field, pattern='^(edit_field_|cancel_edit_item)')],
            EDIT_VALUE: [
                MessageHandler(Filters.text & ~Filters.command, admin_receive_edit_text),
                CallbackQueryHandler(admin_receive_edit_inline, pattern='^edit_val_')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(edit_conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(admin_show_edit_list, pattern='^admin_edit_list$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_show_remove_list, pattern='^admin_remove_item$'))
    dispatcher.add_handler(CallbackQueryHandler(admin_execute_removal, pattern='^delete_item_'))

    # 4d. Admin HITL Price Quote Approval Conversation
    approval_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_admin_decision, pattern='^(approve|modify)_')
        ],
        states={
            WAITING_FOR_ADMIN_FEEDBACK: [
                MessageHandler(Filters.text & ~Filters.command, receive_admin_feedback)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_feedback)],
        allow_reentry=True
    )
    dispatcher.add_handler(approval_conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(contact_expert, pattern='^contact_expert_submit$'))

    # 4e. Text Spec to Channel Post Conversation
    text_post_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_text_post_start, pattern='^admin_text_post_start$')],
        states={
            WAIT_TEXT_POST_SPEC: [MessageHandler(Filters.text & ~Filters.command, admin_receive_text_post_spec)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(text_post_conv)

    # 4f. Story-to-Post Vision Conversation
    story_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_story_start, pattern='^admin_story_to_post$')],
        states={
            WAIT_STORY_PHOTO: [MessageHandler(Filters.photo, admin_receive_story_photo)],
            STORY_FEEDBACK: [MessageHandler(Filters.text & ~Filters.command, admin_receive_story_feedback)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(story_conv)
    dispatcher.add_handler(CallbackQueryHandler(handle_story_callback, pattern='^story_'))

    # 4g. Mass Broadcast Conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern='^admin_broadcast_start$')],
        states={
            WAIT_BROADCAST_CONFIRM: [CallbackQueryHandler(admin_broadcast_choice, pattern='^(broadcast_confirm_default|broadcast_write_custom|cancel_broadcast)$')],
            WAIT_BROADCAST_CUSTOM_TEXT: [MessageHandler(Filters.text & ~Filters.command, admin_receive_custom_broadcast)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dispatcher.add_handler(broadcast_conv)

    # 5. Customer Pricing Wizard Flow
    pricing_wizard_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_pricing_wizard, pattern='^menu_pricing$'),
            CallbackQueryHandler(start_pricing_wizard, pattern='^pricing_restart$'),
        ],
        states={
            PRICING_SELECT_SERIES: [CallbackQueryHandler(handle_series_step, pattern='^pricing_')],
            PRICING_SELECT_MODEL: [CallbackQueryHandler(handle_model_step, pattern='^pricing_')],
            PRICING_SELECT_STORAGE: [CallbackQueryHandler(handle_storage_step, pattern='^pricing_')],
            PRICING_SELECT_BATTERY: [CallbackQueryHandler(handle_battery_step, pattern='^pricing_')],
            PRICING_SELECT_REGISTRY: [CallbackQueryHandler(handle_registry_step, pattern='^pricing_')],
            PRICING_SELECT_PART: [CallbackQueryHandler(handle_part_step, pattern='^pricing_')],
            PRICING_SELECT_CONDITION: [CallbackQueryHandler(handle_condition_step, pattern='^pricing_')],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_pricing_wizard, pattern='^pricing_cancel$'),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    dispatcher.add_handler(pricing_wizard_conv)
    dispatcher.add_handler(CallbackQueryHandler(handle_admin_approval_callback, pattern='^(approve|modify)_'))

    # 6. Global Message Routers
    dispatcher.add_handler(MessageHandler(Filters.contact, handle_contact))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, admin_chat_router))
    dispatcher.add_handler(MessageHandler(Filters.command, fallback_unknown))

    logger.info("All modular handlers registered successfully on Dispatcher.")
    return dispatcher
