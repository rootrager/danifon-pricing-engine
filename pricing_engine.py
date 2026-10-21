# pricing_engine.py — Backward-compatible pricing wrapper
from services.pricing_service import (
    MpTable,
    TIER_MARGINS,
    REGISTRY_FEES,
    BATTERY_COEF,
    OLDER_BATTERY_COEF,
    CONDITION_SCORES,
    calculate_price,
    get_available_capacities,
    get_available_models,
    _load_mp_table,
    _find_model,
    _lookup_mp,
    _fmt,
    _classify_tier,
    _fixed_margin,
)
