import os
import sqlite3
import pytest
import db_manager

def test_db_init_and_connection():
    conn = db_manager.get_connection()
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    expected_tables = [
        "Users", "Inventory", "Orders", "AdminFeedback",
        "Accounting", "InstallmentContracts", "SalesInvoice",
        "SmartDevices", "StoryDrafts", "StoryFeedback"
    ]
    for table in expected_tables:
        assert table in tables, f"Table {table} should exist in database"

def test_user_crud():
    test_uid = 999000111
    db_manager.add_user(test_uid, "testuser", "Test", "+989120000000")
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Username, Phone_Number FROM Users WHERE User_ID = ?", (test_uid,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "testuser"
    assert row[1] == "+989120000000"

def test_smart_devices_crud_and_dashboard():
    test_imei = "359999999999999"
    # 1. Add device
    success = db_manager.add_smart_device(
        imei=test_imei,
        model="iPhone 15 Pro Test",
        buy_price=70_000_000,
        hamta_status="no",
        condition_notes="Clean battery 90%"
    )
    assert success is True
    
    # 2. Search
    search_res = db_manager.search_devices("iPhone 15 Pro Test")
    assert test_imei in search_res
    
    # 3. Sell device
    sell_success = db_manager.sell_smart_device(
        imei=test_imei,
        sell_price=78_000_000,
        hamta_status="no"
    )
    assert sell_success is True
    
    # 4. Pending Hamta
    pending = db_manager.get_pending_hamta()
    matching_pending = [p for p in pending if p[0] == test_imei]
    assert len(matching_pending) == 1
    
    # 5. Mark Hamta done
    hamta_done = db_manager.mark_smart_device_hamta_done(test_imei)
    assert hamta_done is True
    
    # 6. Dashboard metrics
    dash = db_manager.get_store_dashboard()
    assert isinstance(dash, dict)
    assert "in_stock_count" in dash
    assert "sold_count" in dash
    assert "revenue" in dash
    assert "profit" in dash

def test_story_draft_and_feedback():
    draft_id = db_manager.save_story_draft(
        admin_id=844894504,
        image_path="/tmp/test.jpg",
        draft_text="Test Story Post"
    )
    assert draft_id is not None
    
    draft = db_manager.get_story_draft(draft_id)
    assert draft['current_draft'] == "Test Story Post"
    
    db_manager.update_story_draft(draft_id, "Updated Story Post")
    updated = db_manager.get_story_draft(draft_id)
    assert updated['current_draft'] == "Updated Story Post"
    
    db_manager.save_story_feedback(draft_id, 844894504, "Change price to 80m")
    feedback = db_manager.get_recent_story_feedback(limit=5)
    assert "Change price to 80m" in feedback
