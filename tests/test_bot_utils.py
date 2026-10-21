import pytest
from unittest.mock import MagicMock
from bot_utils import send_chunked_message

def test_send_chunked_message_short_text():
    mock_bot = MagicMock()
    mock_bot.send_message.return_value = "sent_msg"
    
    res = send_chunked_message(mock_bot, 123456, "Short message", reply_markup="kb")
    assert len(res) == 1
    mock_bot.send_message.assert_called_once_with(
        chat_id=123456,
        text="Short message",
        reply_markup="kb",
        parse_mode="HTML"
    )

def test_send_chunked_message_markdown_fallback():
    mock_bot = MagicMock()
    # First call with parse_mode="Markdown" raises BadRequest, second call with parse_mode=None succeeds
    mock_bot.send_message.side_effect = [Exception("Can't parse entities"), "sent_msg_fallback"]
    
    res = send_chunked_message(mock_bot, 123456, "Unclosed *markdown text", reply_markup="kb", parse_mode="Markdown")
    assert res == ["sent_msg_fallback"]
    assert mock_bot.send_message.call_count == 2
    assert mock_bot.send_message.call_args_list[0].kwargs['parse_mode'] == "Markdown"
    assert mock_bot.send_message.call_args_list[1].kwargs['parse_mode'] is None

def test_send_chunked_message_long_text():
    mock_bot = MagicMock()
    mock_bot.send_message.return_value = "sent_msg"
    
    # Create text longer than 4096 chars with newlines
    long_text = "\n".join([f"Line {i}: some product information details" for i in range(200)])
    assert len(long_text) > 4096
    
    res = send_chunked_message(mock_bot, 123456, long_text, reply_markup="kb")
    assert len(res) > 1
    
    # Ensure reply_markup was only given on the last call
    calls = mock_bot.send_message.call_args_list
    assert calls[0].kwargs['reply_markup'] is None
    assert calls[-1].kwargs['reply_markup'] == "kb"
