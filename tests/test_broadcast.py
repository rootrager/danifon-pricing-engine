import pytest
from unittest.mock import MagicMock, patch
from services import marketing_service
from handlers import admin_panel

def test_broadcast_template_format():
    template = marketing_service.DEFAULT_BROADCAST_TEMPLATE
    formatted = template.format(name="مهدی")
    assert "دانیال هستم از دانیفون" in formatted
    assert "سلام مهدی عزیز" in formatted

@patch("services.marketing_service.get_broadcast_users")
def test_broadcast_users_fetch(mock_get_users):
    mock_get_users.return_value = [(12345, "مهدی"), (67890, "علی")]
    users = marketing_service.get_broadcast_users()
    assert len(users) == 2
    assert users[0][1] == "مهدی"

def test_execute_broadcast_job():
    mock_bot = MagicMock()
    with patch("services.marketing_service.get_broadcast_users") as mock_users:
        mock_users.return_value = [(101, "مهدی"), (102, "رضا")]
        marketing_service.execute_broadcast_job(mock_bot, 9999, marketing_service.DEFAULT_BROADCAST_TEMPLATE)
        
        # Verify 2 messages sent to users + 1 summary message to admin
        assert mock_bot.send_message.call_count == 3
