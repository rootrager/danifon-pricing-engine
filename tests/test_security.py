import pytest
from unittest.mock import MagicMock
from core.security import (
    is_authorized_admin,
    admin_required,
    sanitize_imei,
    sanitize_amount,
    sanitize_text,
)
from core.config import AUTHORIZED_ADMINS

def test_is_authorized_admin():
    admin_id = AUTHORIZED_ADMINS[0]
    fake_user_id = 11223344
    assert is_authorized_admin(admin_id) is True
    assert is_authorized_admin(fake_user_id) is False

def test_admin_required_decorator_allows_admin():
    @admin_required
    def protected_handler(update, context):
        return "success"

    mock_update = MagicMock()
    mock_update.effective_user.id = AUTHORIZED_ADMINS[0]
    mock_context = MagicMock()

    result = protected_handler(mock_update, mock_context)
    assert result == "success"

def test_admin_required_decorator_blocks_unauthorized():
    @admin_required
    def protected_handler(update, context):
        return "success"

    mock_update = MagicMock()
    mock_update.effective_user.id = 999999999
    mock_update.callback_query = MagicMock()
    mock_context = MagicMock()

    result = protected_handler(mock_update, mock_context)
    assert result is None
    mock_update.callback_query.answer.assert_called_once_with("⛔ دسترسی غیرمجاز.", show_alert=True)

def test_sanitize_imei():
    valid_imei = "359999999999999"
    assert sanitize_imei(valid_imei) == "359999999999999"
    assert sanitize_imei(" 359-999-999-999-999 ") == "359999999999999"

    with pytest.raises(ValueError):
        sanitize_imei("")

    with pytest.raises(ValueError):
        sanitize_imei("123; DROP TABLE Users;")

def test_sanitize_amount():
    assert sanitize_amount("50,000,000") == 50000000.0
    assert sanitize_amount(85000000) == 85000000.0
    assert sanitize_amount("۵۰,۰۰۰,۰۰۰") == 50000000.0

    with pytest.raises(ValueError):
        sanitize_amount("-5000")

    with pytest.raises(ValueError):
        sanitize_amount("invalid_number")

def test_sanitize_text():
    assert sanitize_text("  hello world  ") == "hello world"
    assert len(sanitize_text("a" * 5000, max_len=100)) == 100
    assert sanitize_text(None) == ""
