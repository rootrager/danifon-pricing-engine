import pytest
from pricing_engine import (
    calculate_price,
    get_available_capacities,
    get_available_models,
    _classify_tier,
    _fixed_margin,
    TIER_MARGINS,
    REGISTRY_FEES,
)

def test_classify_tier():
    assert _classify_tier("iPhone 17 Pro Max") == "flagship"
    assert _classify_tier("iPhone 16 Pro Max") == "flagship"
    assert _classify_tier("iPhone 16 Pro") == "pro"
    assert _classify_tier("iPhone 15 Pro Max") == "pro"
    assert _classify_tier("iPhone 15") == "mid"
    assert _classify_tier("iPhone 14 Plus") == "mid"
    assert _classify_tier("iPhone 13 Pro") == "pro"
    assert _classify_tier("iPhone 13") == "older"
    assert _classify_tier("iPhone 11") == "older"

def test_fixed_margin():
    assert _fixed_margin(40_000_000) == 800_000
    assert _fixed_margin(75_000_000) == 1_000_000
    assert _fixed_margin(150_000_000) == 1_800_000
    assert _fixed_margin(250_000_000) == 2_500_000
    assert _fixed_margin(350_000_000) == 3_500_000

def test_get_available_models():
    models = get_available_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "iPhone 16 Pro Max" in models or "iPhone 13" in models

def test_get_available_capacities():
    caps = get_available_capacities("iPhone 16 Pro Max")
    assert isinstance(caps, list)
    assert len(caps) > 0

def test_calculate_price_registered_success():
    res = calculate_price(
        model="iPhone 16 Pro Max",
        capacity="256",
        battery=95,
        register="Registered",
        condition="Clean"
    )
    assert res["success"] is True
    assert res["mp"] > 0
    assert res["sell_price"] > 0
    assert res["buy_price"] > 0
    assert res["buy_price"] < res["sell_price"]
    assert "breakdown" in res

def test_calculate_price_unregistered():
    res = calculate_price(
        model="iPhone 16 Pro Max",
        capacity="256",
        battery=100,
        register="Unregistered",
        condition="Clean"
    )
    assert res["success"] is True
    assert "register_deduction" in res["breakdown"]

def test_calculate_price_invalid_model():
    res = calculate_price(
        model="iPhone 99 Fake Model",
        capacity="128",
        battery=100,
        register="Registered",
        condition="Clean"
    )
    assert res["success"] is False
    assert "error" in res

def test_calculate_price_kb_unregistered_conversion():
    """Verify that querying a Registered device when KB benchmark is Unregistered correctly adds registry fee."""
    res_reg = calculate_price(
        model="iPhone 16 Pro",
        capacity="128",
        battery=99,
        register="Registered",
        condition="Clean"
    )
    res_unreg = calculate_price(
        model="iPhone 16 Pro",
        capacity="128",
        battery=99,
        register="Unregistered",
        condition="Clean"
    )
    assert res_reg["success"] is True
    assert res_unreg["success"] is True
    # Registered price must be significantly higher than unregistered price (at least by registry fee ~68M)
    assert res_reg["buy_price"] > res_unreg["buy_price"] + 60_000_000
