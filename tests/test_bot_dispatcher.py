import pytest
from unittest.mock import MagicMock
from telegram.ext import Dispatcher, ConversationHandler, CommandHandler, CallbackQueryHandler
from bot import setup_dispatcher

def test_setup_dispatcher_registration():
    mock_bot = MagicMock()
    dispatcher = Dispatcher(mock_bot, None, workers=0, use_context=True)
    
    returned_disp = setup_dispatcher(dispatcher)
    assert returned_disp is dispatcher
    
    # Check that handlers were registered
    assert len(dispatcher.handlers) > 0
    all_registered_handlers = []
    for group, handlers in dispatcher.handlers.items():
        all_registered_handlers.extend(handlers)
        
    handler_types = [type(h) for h in all_registered_handlers]
    assert CommandHandler in handler_types
    assert CallbackQueryHandler in handler_types
    assert ConversationHandler in handler_types
