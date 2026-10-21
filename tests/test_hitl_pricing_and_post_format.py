import json
import pytest
from core import database
from services import marketing_service

def test_channel_post_formatting():
    raw_spec = "آیفون 13 پرو مکس 128، رنگ آبی سیرا، تک سیم LL/A باتری 83 - قیمت 129 میلیون"
    res = marketing_service.create_channel_post_from_text_spec(raw_spec)
    
    text = res["text"]
    assert '● <a href="https://t.me/daniphoneir">DaniFone</a> | Apple Store' in text
    assert "📱 iPhone 13 Pro Max" in text
    assert "وضعیت: کارکرده" in text
    assert "رنگ: آبی سیرا" in text
    assert "ظرفیت: 128GB" in text
    assert "پارتنامبر و سیمکارت: LL/A | تک سیمکارت" in text
    assert "رجیستری: رجیستر شده" in text
    assert "باتری: 83%" in text
    assert "قیمت: 129.000" in text

def test_pricing_request_db_persistence():
    req_id = "test_req_99"
    database.save_pricing_request(
        request_id=req_id,
        user_id=123456,
        user_full_name="Mahdi",
        username="mahdidev",
        user_specs_raw="iPhone 13 Pro Max 128GB",
        quote_json=json.dumps({"model": "iPhone 13 Pro Max", "buy_price": 129000000})
    )
    
    req = database.get_pricing_request(req_id)
    assert req is not None
    assert req["user_id"] == 123456
    assert req["status"] == "pending"
    
    database.update_pricing_request(req_id, status="approved", final_price=129000000)
    updated_req = database.get_pricing_request(req_id)
    assert updated_req["status"] == "approved"
    assert updated_req["final_price"] == 129000000

def test_format_channel_price_variations():
    assert marketing_service.format_channel_price("129000000") == "129.000"
    assert marketing_service.format_channel_price("129.000") == "129.000"
    assert marketing_service.format_channel_price("53000000") == "53.000"
    assert marketing_service.format_channel_price("172000000") == "172.000"

def test_price_variance_analysis_and_continuous_learning():
    from handlers.pricing import analyze_price_variance, extract_expert_reason
    
    # Test extract_expert_reason
    reason1 = extract_expert_reason("162.5m به علت وجود خط و خش فریم")
    assert reason1 == "به علت وجود خط و خش فریم"

    reason2 = extract_expert_reason("165000000 - افت 2 درصدی بازار")
    assert reason2 == "افت 2 درصدی بازار"

    # Test underestimation with reason
    res_under = analyze_price_variance(100_000_000, 110_000_000, "iPhone 15 Pro", expert_reason="داشتن گارانتی معتبر")
    assert res_under["direction"] == "UNDERESTIMATED"
    assert res_under["difference"] == 10_000_000
    assert res_under["variance_pct"] == 10.0
    assert "داشتن گارانتی معتبر" in res_under["analysis_insight"]
    
    # Test overestimation
    res_over = analyze_price_variance(200_000_000, 180_000_000, "iPhone 16 Pro Max")
    assert res_over["direction"] == "OVERESTIMATED"
    assert res_over["difference"] == -20_000_000
    assert res_over["variance_pct"] == -10.0
    
    # Test matched
    res_match = analyze_price_variance(150_000_000, 150_000_000, "iPhone 14 Pro")
    assert res_match["direction"] == "MATCHED"
    assert res_match["variance_pct"] == 0.0

    # Test database persistence of feedback
    database.add_feedback(
        agent_action="iPhone 15 Pro 128GB",
        admin_response="185000000 به علت تمیزی",
        corrected_data=json.dumps(res_under, ensure_ascii=False)
    )
    recent = database.get_recent_admin_feedback(limit=1)
    assert len(recent) > 0
    assert recent[0]["agent_action"] == "iPhone 15 Pro 128GB"
