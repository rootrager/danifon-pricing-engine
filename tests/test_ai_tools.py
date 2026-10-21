import json
import pytest
from ai.tools import (
    tool_add_device,
    tool_register_sale,
    tool_draft_channel_post,
    tool_get_report,
    tool_search_inventory,
    tool_get_market_price,
    tool_get_registry_fees,
    tool_get_market_context,
    tool_query_knowledge_base,
)

def test_tool_add_and_search_device():
    test_imei = "358888888888888"
    res_str = tool_add_device(
        imei=test_imei,
        model="iPhone 14 Pro Max Test",
        buy_price=95_000_000,
        hamta_status="yes",
        condition="Battery 88%, clean"
    )
    res = json.loads(res_str)
    assert res.get("success") is True
    assert res.get("imei") == test_imei

    search_output = tool_search_inventory("iPhone 14 Pro Max Test")
    assert test_imei in search_output

def test_tool_register_sale():
    test_imei = "358888888888888"
    res_str = tool_register_sale(
        imei=test_imei,
        sell_price=105_000_000,
        payment_notes="Cash payment in full",
        is_hamta_done=True
    )
    res = json.loads(res_str)
    assert res.get("success") is True
    assert res.get("imei") == test_imei

def test_tool_draft_channel_post():
    res_str = tool_draft_channel_post(
        imei="358888888888888",
        proposed_price=110_000_000,
        text="iPhone 14 Pro Max clean device"
    )
    res = json.loads(res_str)
    assert res.get("action") == "channel_draft"
    assert res.get("proposed_price") == 110000000.0

def test_tool_get_report():
    res_str = tool_get_report()
    res = json.loads(res_str)
    assert "dashboard" in res
    assert "pending_hamta" in res

def test_tool_get_market_price():
    res_str = tool_get_market_price("iPhone 13")
    res = json.loads(res_str)
    assert isinstance(res, dict)
    assert len(res) > 0

def test_tool_get_registry_fees():
    res_str = tool_get_registry_fees()
    res = json.loads(res_str)
    assert isinstance(res, dict)
    assert "iPhone 16 Pro Max" in res

def test_tool_get_market_context():
    res_str = tool_get_market_context()
    res = json.loads(res_str)
    assert "usd_rate" in res
    assert "market_condition" in res

def test_tool_query_knowledge_base():
    res_str = tool_query_knowledge_base("13 Pro")
    # Returns JSON list or string
    assert "13 Pro" in res_str or "13" in res_str
