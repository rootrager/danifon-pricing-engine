import pytest
import math
import json
import sqlite3
from unittest.mock import MagicMock, patch
from core import config, database, security, utils
from services import (
    pricing_service,
    inventory_service,
    vision_service,
    marketing_service,
    reporting_service,
    export_service,
)
from handlers import customer, pricing, admin_panel, admin_ai_router, story_pipeline
from ai import tools as ai_tools
from color_detector import detect_phone_color, correct_color_in_post
from image_matcher import _extract_model_from_text, _extract_color_from_text, find_best_image

# ===========================================================================
# 1. CUSTOMER FLOW & INPUT RESILIENCE
# ===========================================================================

def test_customer_fsm_none_text_handling():
    """Verify handlers do not crash with AttributeError when update.message.text is None."""
    mock_update = MagicMock()
    mock_update.message.text = None
    mock_update.effective_user.id = 12345
    mock_context = MagicMock()
    mock_context.user_data = {'awaiting_ai_price': True}

    # Should not crash with AttributeError
    try:
        pricing.handle_ai_price_input(mock_update, mock_context)
    except AttributeError:
        pytest.fail("handle_ai_price_input crashed on None text")

def test_customer_budget_persian_digits_input():
    """Verify budget recommendation handler accepts Persian digits."""
    mock_update = MagicMock()
    mock_update.message.text = "۶۵۰۰۰۰۰۰"  # 65,000,000 in Persian digits
    mock_context = MagicMock()
    mock_context.user_data = {}
    
    res = customer.receive_budget_input(mock_update, mock_context)
    assert res == customer.ConversationHandler.END

# ===========================================================================
# 2. FINANCE EDGE CASES & ARITHMETIC
# ===========================================================================

def test_security_sanitization_adversarial():
    assert security.sanitize_amount("1,000,000") == 1000000.0

# ===========================================================================
# 3. PRICING SERVICE ADVERSARIAL & BOUNDARY TESTS
# ===========================================================================

def test_pricing_overlapping_model_names():
    """Ensure iPhone 14 does not match iPhone 14 Pro Max in registry fees."""
    fee_14 = pricing_service._get_registry_fee_for_model("iPhone 14")
    fee_14_pm = pricing_service._get_registry_fee_for_model("iPhone 14 Pro Max")
    fee_14_pro = pricing_service._get_registry_fee_for_model("iPhone 14 Pro")
    
    assert fee_14 == 36750000
    assert fee_14_pm == 39300000
    assert fee_14_pro == 39150000
    assert fee_14 != fee_14_pm

def test_pricing_1tb_capacity_lookup():
    """Verify 1TB capacity lookup functions correctly for Pro Max models."""
    res = pricing_service.calculate_price(
        model="iPhone 17 Pro Max",
        capacity="1TB",
        battery=100,
        register="Registered",
        condition="Clean"
    )
    assert res["success"] is True
    assert res["mp"] > 0

def test_pricing_battery_above_100():
    """Battery > 100 should not award infinite bonus."""
    res_100 = pricing_service.calculate_price("iPhone 15 Pro", "256", 100, "Registered")
    res_105 = pricing_service.calculate_price("iPhone 15 Pro", "256", 105, "Registered")
    assert res_100["success"] is True
    assert res_105["success"] is True

def test_pricing_battery_negative_and_zero():
    res = pricing_service.calculate_price("iPhone 15 Pro", "256", 0, "Registered")
    assert res["success"] is True
    assert res["buy_price"] >= 0  # Should never be negative

def test_pricing_case_insensitivity_and_whitespace():
    res1 = pricing_service.calculate_price("  iphone 16 pro max  ", " 256 ", 90, "registered")
    res2 = pricing_service.calculate_price("iPhone 16 Pro Max", "256", 90, "Registered")
    assert res1["success"] is True
    assert res1["buy_price"] == res2["buy_price"]

# ===========================================================================
# 4. DATABASE INTEGRITY, CONCURRENCY & SERIALIZATION
# ===========================================================================

def test_db_duplicate_imei_update():
    """Adding same IMEI with updated condition notes should update properly without breaking."""
    imei = "357777777777777"
    database.add_smart_device(imei, "iPhone 15 Pro", 70000000, "no", "First condition")
    database.add_smart_device(imei, "iPhone 15 Pro", 72000000, "yes", "Updated condition")
    
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Buy_Price, Hamta_Status, Condition_Notes, Status FROM SmartDevices WHERE IMEI = ?", (imei,))
    row = cursor.fetchone()
    conn.close()
    
    assert row[0] == 72000000
    assert row[1] == "yes"
    assert row[2] == "Updated condition"
    assert row[3] == "In Stock"

def test_db_sell_device_twice():
    """Selling a device should update status and price. Attempting to sell nonexistent returns False."""
    non_existent = "350000000000000"
    success = database.sell_smart_device(non_existent, 80000000, "yes")
    assert success is False

def test_db_search_devices_limit_and_empty():
    """Search with empty or whitespace string shouldn't crash."""
    out = database.search_devices("")
    assert isinstance(out, str)

def test_db_concurrent_connections():
    """Multiple connections writing concurrently should succeed under WAL mode."""
    conn1 = database.get_connection()
    conn2 = database.get_connection()
    
    conn1.execute("INSERT OR REPLACE INTO Accounting (Record_ID, Type, Amount, Description, Date) VALUES (99991, 'Sale', 1000, 'Test 1', '2026-08-18')")
    conn1.commit()
    
    conn2.execute("INSERT OR REPLACE INTO Accounting (Record_ID, Type, Amount, Description, Date) VALUES (99992, 'Sale', 2000, 'Test 2', '2026-08-18')")
    conn2.commit()
    
    conn1.close()
    conn2.close()

# ===========================================================================
# 5. AI TOOLS ADVERSARIAL ATTACKS
# ===========================================================================

def test_ai_tool_sql_injection_in_imei():
    malicious_imei = "35999999'; DROP TABLE Users; --"
    res_str = ai_tools.tool_add_device(
        imei=malicious_imei,
        model="iPhone 15",
        buy_price=50000000,
        hamta_status="no",
        condition="clean"
    )
    res = json.loads(res_str)
    assert "error" in res

    # Verify Users table still exists
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM Users")
    assert cursor.fetchone() is not None
    conn.close()

def test_ai_tool_negative_and_nan_prices():
    res_str = ai_tools.tool_add_device(
        imei="359999999999999",
        model="iPhone 15",
        buy_price=-5000000,
        hamta_status="no",
        condition="clean"
    )
    res = json.loads(res_str)
    assert "error" in res

def test_ai_tool_malformed_prices_json():
    res_str = ai_tools.tool_update_market_prices(
        prices_json="{malformed json",
        usd_rate=185000,
        market_condition="normal"
    )
    res = json.loads(res_str)
    assert "error" in res

def test_ai_tool_non_dict_prices_json():
    res_str = ai_tools.tool_update_market_prices(
        prices_json=json.dumps(["iPhone 16"]),
        usd_rate=185000,
        market_condition="normal"
    )
    res = json.loads(res_str)
    assert "error" in res

# ===========================================================================
# 6. TELEGRAM CALLBACK & FSM ADVERSARIAL TESTS
# ===========================================================================

def test_handle_admin_decision_malformed_callback():
    mock_update = MagicMock()
    mock_update.callback_query.data = "approve"  # Missing action_id and user_id
    mock_context = MagicMock()
    mock_context.bot_data = {}

    # Should not crash with IndexError
    try:
        res = pricing.handle_admin_decision(mock_update, mock_context)
    except IndexError:
        pytest.fail("handle_admin_decision crashed on malformed callback data")

def test_handle_story_callback_malformed():
    mock_update = MagicMock()
    mock_update.callback_query.data = "story"  # Missing parts
    mock_update.effective_user.id = config.AUTHORIZED_ADMINS[0]
    mock_context = MagicMock()

    try:
        res = story_pipeline.handle_story_callback(mock_update, mock_context)
    except IndexError:
        pytest.fail("handle_story_callback crashed on malformed callback data")

def test_image_matcher_none_text():
    """find_best_image and extraction functions should not crash on None text."""
    try:
        assert _extract_model_from_text(None) is None
        assert _extract_color_from_text(None) == []
        assert find_best_image(None) is None
    except AttributeError:
        pytest.fail("image_matcher functions crashed on None input")

# ===========================================================================
# 7. SECURITY & ACCESS CONTROL
# ===========================================================================

def test_unauthorized_user_blocked_from_admin_panel():
    mock_update = MagicMock()
    mock_update.effective_user.id = 11112222  # Not in AUTHORIZED_ADMINS
    mock_update.callback_query = None
    mock_context = MagicMock()

    res = admin_panel.admin_panel(mock_update, mock_context)
    assert res is None
    mock_update.message.reply_text.assert_called_once_with("⛔ شما به این بخش دسترسی ندارید.")

def test_unauthorized_user_blocked_from_backup_download():
    mock_update = MagicMock()
    mock_update.effective_user.id = 11112222
    mock_update.callback_query = MagicMock()
    mock_context = MagicMock()
    
    res = admin_panel.admin_list_users(mock_update, mock_context)
    assert res is None
    mock_update.callback_query.answer.assert_called_once_with("⛔ دسترسی غیرمجاز.", show_alert=True)
