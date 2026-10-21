import json
import re
import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from core.config import MP_TABLE_PATH, MARKET_CONTEXT_PATH, KNOWLEDGE_BASE_PATH

logger = logging.getLogger(__name__)

# mp_table schema: {"iPhone 15 Pro": {"256": 153966667, ...}, ...}
MpTable = Dict[str, Dict[str, int]]
_CAPACITY_ORDER = ["64", "128", "256", "512", "1TB"]

TIER_MARGINS = {
    "flagship": 0.18,
    "pro":      0.20,
    "mid":      0.25,
    "older":    0.28,
}

# Official Iranian Customs Duty Rates (نرخ عوارض گمرکی ایران به تومان)
CUSTOMS_DUTY_RATES = {
    "iPhone 17 Pro Max": 116_500_000,
    "iPhone 17 Pro":     107_250_000,
    "iPhone 17 Air":      94_050_000,
    "iPhone 17":          75_050_000,
    "iPhone 16 Pro Max":  73_900_000,
    "iPhone 16 Pro":      68_100_000,
    "iPhone 16 Plus":     72_400_000,
    "iPhone 16":          59_250_000,
    "iPhone 16e":         51_100_000,
    "iPhone 15 Pro Max":  67_850_000,
    "iPhone 15 Pro":      59_350_000,
    "iPhone 15 Plus":     57_700_000,
    "iPhone 15":          51_850_000,
    "iPhone 14 Pro Max":  19_300_000,
    "iPhone 14 Pro":      19_150_000,
    "iPhone 14 Plus":     17_550_000,
    "iPhone 14":          16_750_000,
    "iPhone 13 Pro Max":  15_300_000,
    "iPhone 13 Pro":      14_600_000,
    "iPhone 13":          13_000_000,
    "iPhone 13 mini":     15_050_000,
    "iPhone 12 Pro Max":   9_750_000,
    "iPhone 12 Pro":      15_850_000,
    "iPhone 12":           9_650_000,
    "iPhone 12 mini":      8_450_000,
    "iPhone 11 Pro Max":   8_600_000,
    "iPhone 11 Pro":       7_450_000,
    "iPhone 11":           7_250_000,
    "iPhone XS Max":       6_900_000,
    "iPhone XS":           5_900_000,
    "iPhone XR":           7_700_000,
    "iPhone X":            6_700_000,
    "Samsung Galaxy S26 Ultra": 85_500_000,
    "Samsung Galaxy S25 Ultra": 65_850_000,
    "Samsung Galaxy S24 Ultra": 70_250_000,
    "Samsung Galaxy S23 Ultra": 19_600_000,
    "Samsung Galaxy Z Fold 7": 111_150_000,
}

PASSPORT_REGISTRATION_FEE = 20_000_000

REGISTRY_FEES = {
    model: duty + PASSPORT_REGISTRATION_FEE
    for model, duty in CUSTOMS_DUTY_RATES.items()
}

BATTERY_COEF = 0.003
OLDER_BATTERY_COEF = 0.0025

CONDITION_SCORES = {
    "Akband":           1_000_000,
    "Clean":                    0,
    "Minor Scratches":   -500_000,
    "Frame Damage":    -2_000_000,
}

def _fmt(amount: int) -> str:
    """Format amount with thousand-separators."""
    return f"{amount:,}"

def format_5m_range(buy_price: int) -> Tuple[int, int, str]:
    """
    Computes a 5-Million Toman dynamic price range around buy_price.
    Example: 253,950,000 Toman -> Min: 253,000,000, Max: 258,000,000.
    Returns: (buy_min, buy_max, range_formatted_string)
    """
    if buy_price <= 0:
        return 0, 0, "0 تومان"
    
    base_m = (buy_price // 1_000_000) * 1_000_000
    buy_min = base_m
    buy_max = base_m + 5_000_000
    
    range_str = f"{_fmt(buy_min)} تا {_fmt(buy_max)} تومان"
    return buy_min, buy_max, range_str

def _load_mp_table() -> MpTable:
    """Load nested MP table; auto-convert legacy flat keys if needed."""
    if not os.path.exists(MP_TABLE_PATH):
        return {}
    with open(MP_TABLE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not raw:
        return {}

    sample = next((v for k, v in raw.items() if k != "comment"), None)
    if isinstance(sample, dict):
        return {k: v for k, v in raw.items() if k != "comment" and isinstance(v, dict)}

    nested: MpTable = {}
    for key, price in raw.items():
        if key == "comment" or not isinstance(price, (int, float)):
            continue
        model, _, capacity = key.rpartition(" ")
        nested.setdefault(model, {})[capacity] = int(price)
    return nested

def _find_model(model: str, mp_table: MpTable) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
    """Case-insensitive model lookup; returns canonical name and capacity map."""
    model = model.strip()
    if model in mp_table:
        return model, mp_table[model]

    lower = model.lower()
    for name, caps in mp_table.items():
        if name.lower() == lower:
            return name, caps
    return None, None

def get_available_capacities(model: str) -> List[str]:
    """Return storage capacities available in mp_table for the given model."""
    mp_table = _load_mp_table()
    _, caps = _find_model(model, mp_table)
    if not caps:
        return []
    return sorted(
        caps.keys(),
        key=lambda c: _CAPACITY_ORDER.index(c) if c in _CAPACITY_ORDER else 99,
    )

def get_available_models() -> List[str]:
    """Return all model names present in mp_table."""
    return sorted(_load_mp_table().keys())

def _lookup_mp(
    model: str,
    capacity: str,
    mp_table: MpTable,
) -> Tuple[Optional[int], Optional[str], str]:
    capacity = capacity.strip()
    canonical, caps = _find_model(model, mp_table)
    lookup_key = f"{model.strip()} {capacity}"

    if caps is None:
        error = (
            f"❌ Model <b>{model.strip()}</b> was not found in the price database.\n\n"
            "Please check the model name (e.g. <code>iPhone 15 Pro</code>) "
            "and type /start to try again."
        )
        return None, error, lookup_key

    mp = caps.get(capacity)
    if mp is None:
        cap_clean = capacity.upper().replace(" ", "").replace("GB", "")
        if cap_clean in ["1TB", "1024", "1T"]:
            mp = caps.get("1TB") or caps.get("1024")
        else:
            mp = caps.get(cap_clean) or caps.get(f"{cap_clean}GB")

    if mp is None:
        caps_str = ", ".join(
            sorted(caps.keys(), key=lambda c: _CAPACITY_ORDER.index(c) if c in _CAPACITY_ORDER else 99)
        )
        error = (
            f"❌ Capacity <b>{capacity}</b> is not available for "
            f"<b>{canonical}</b>.\n\n"
            f"Supported capacities: <code>{caps_str}</code>\n\n"
            "Please select a valid capacity or type /start to try again."
        )
        return None, error, lookup_key

    return int(mp), None, f"{canonical} {capacity}"

def _classify_tier(model: str) -> str:
    m = model.lower()
    if re.search(r"iphone\s*(17|16)\s*pro\s*max", m):
        return "flagship"
    if "pro" in m:
        return "pro"
    if re.search(r"iphone\s*(14|15|16|17)", m) or re.search(r"se\s*(2022|3)", m):
        return "mid"
    return "older"

def _fixed_margin(mp: int) -> int:
    if mp < 50_000_000:
        return 800_000
    if mp < 100_000_000:
        return 1_000_000
    if mp < 200_000_000:
        return 1_800_000
    if mp < 300_000_000:
        return 2_500_000
    return 3_500_000

def _get_customs_duty_for_model(model: str) -> int:
    """Matches official customs duty rate (without passport fee) for model."""
    model_clean = model.lower().strip()
    best_match_fee = 0
    best_match_len = 0
    for m_name, fee in CUSTOMS_DUTY_RATES.items():
        m_lower = m_name.lower()
        if m_lower == model_clean:
            return fee
        if m_lower in model_clean and len(m_lower) > best_match_len:
            best_match_fee = fee
            best_match_len = len(m_lower)
    return best_match_fee

def _get_registry_fee_for_model(model: str) -> int:
    """
    Robust matching for registry fee: matches exact model or longest matching prefix.
    Prevents shorter keys like 'iPhone 14' from incorrectly overriding 'iPhone 14 Pro Max'.
    """
    model_clean = model.lower().strip()
    best_match_fee = 0
    best_match_len = 0
    for m_name, fee in REGISTRY_FEES.items():
        m_lower = m_name.lower()
        if m_lower == model_clean:
            return fee
        if m_lower in model_clean and len(m_lower) > best_match_len:
            best_match_fee = fee
            best_match_len = len(m_lower)
    return best_match_fee

def _find_kb_record(model: str, capacity: str, register: str = "") -> Optional[Dict[str, Any]]:
    """Helper to find matching real transaction record from knowledge_base.json."""
    if not os.path.exists(KNOWLEDGE_BASE_PATH):
        return None
    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            kb = json.load(f)
            
        def norm(m: str) -> str:
            clean = str(m).lower().replace("iphone", "").replace("نرمال", "").replace("normal", "").strip()
            return re.sub(r"\s+", " ", clean)

        nq = norm(model)
        q_series = re.search(r"\b(11|12|13|14|15|16|17|x|xr|xs)\b", nq)
        if not q_series:
            return None
        target_series = q_series.group(1)
        q_words = set(nq.split())
        cap_clean = str(capacity).upper().replace("GB", "").strip()
        is_target_unreg = str(register).lower() in ["unregistered", "بدون رجیستر", "بدون کد"]

        exact_reg_matches = []
        other_matches = []

        for item in kb:
            nm = norm(item.get("model", ""))
            if not re.search(r"\b" + target_series + r"\b", nm):
                continue
            m_words = set(nm.split())
            if ("pro" in q_words) != ("pro" in m_words):
                continue
            if ("max" in q_words) != ("max" in m_words):
                continue
            if ("plus" in q_words) != ("plus" in m_words):
                continue
            item_cap = str(item.get("capacity", "")).upper().replace("GB", "").strip()
            if item_cap and item_cap != cap_clean:
                continue
            if item.get("buy_price") or item.get("sell_price"):
                item_reg_unreg = str(item.get("register", "")).lower() in ["ندارد", "unregistered", "بدون کد"]
                if is_target_unreg == item_reg_unreg:
                    if nm == nq:
                        exact_reg_matches.insert(0, item)
                    else:
                        exact_reg_matches.append(item)
                else:
                    if nm == nq:
                        other_matches.insert(0, item)
                    else:
                        other_matches.append(item)

        matches = exact_reg_matches or other_matches
        return matches[0] if matches else None
    except Exception as e:
        logger.error(f"Error reading KB for price calculation: {e}")
        return None

def _compute_hardware_depreciation(base_price_toman: float, condition_str: str) -> float:
    """
    Computes component replacement depreciation based on real market experience (تجربه بازار آیفون):
    - Base < 100M: 5M Toman per replaced part (Back Glass / LCD / Camera)
    - Base 100M - 200M: 8.5M Toman per replaced part
    - Base 200M - 300M: 13.5M Toman per replaced part
    - Base > 300M: 40M Toman per replaced part
    """
    cond = str(condition_str).lower().replace("_", " ")
    replaced_parts_count = 0
    if any(k in cond for k in ["درب پشت", "back glass", "backglass", "دربپشت"]):
        replaced_parts_count += 1
    if any(k in cond for k in ["ال سی دی", "السیدی", "lcd", "صفحه نمایش", "screen"]):
        replaced_parts_count += 1
    if any(k in cond for k in ["دوربین", "camera"]):
        replaced_parts_count += 1
    if ("تعویض" in cond or "repaired" in cond) and replaced_parts_count == 0:
        replaced_parts_count = 1

    if replaced_parts_count == 0:
        return 0.0

    if base_price_toman < 100_000_000:
        per_part = 5_000_000
    if base_price_toman < 100_000_000:
        per_part = 5_000_000
    elif base_price_toman < 200_000_000:
        per_part = 8_500_000
    elif base_price_toman < 300_000_000:
        per_part = 13_500_000
    else:
        per_part = 40_000_000

    return float(replaced_parts_count * per_part)

def _load_market_usd_rates() -> Tuple[float, float]:
    """Helper to load live target USD rate and base benchmark USD rate from market_context.json."""
    default_target = 210000.0
    default_base = 190000.0
    if not os.path.exists(MARKET_CONTEXT_PATH):
        return default_target, default_base
    try:
        with open(MARKET_CONTEXT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            target = float(data.get("usd_rate", default_target))
            base = float(data.get("base_usd_rate", default_base))
            return target, base
    except Exception:
        return default_target, default_base

def _compute_usd_adjustment(
    base_price_toman: float,
    target_usd_rate: float = 210000.0,
    base_usd_rate: float = 190000.0
) -> float:
    """
    Computes USD rate fluctuation adjustment based on Danifon market formula:
    - Base USD rate benchmark in DB/KB: 190,000 Toman
    - Target USD rate: default 210,000 Toman (balanced rate to prevent bubble)
    - usd_delta_k = (target_usd_rate - base_usd_rate) / 1000.0
    
    Impact per 1,000 Toman USD increase:
    - Phone < 100M Toman: +1,000,000 Toman per 1k USD
    - Phone 100M - 200M Toman: +2,000,000 Toman per 1k USD
    - Phone 200M - 300M Toman: +3,500,000 Toman per 1k USD (3M-4M range)
    - Phone > 300M Toman: +5,000,000 Toman per 1k USD
    """
    usd_delta_k = (target_usd_rate - base_usd_rate) / 1000.0
    if usd_delta_k <= 0:
        return 0.0

    if base_price_toman < 100_000_000:
        rate_per_k = 1_000_000
    elif base_price_toman < 200_000_000:
        rate_per_k = 2_000_000
    elif base_price_toman < 300_000_000:
        rate_per_k = 3_500_000
    else:
        rate_per_k = 5_000_000

    return float(usd_delta_k * rate_per_k)

def calculate_price(
    model: str,
    capacity: str,
    battery: int,
    register: str,
    condition: str = "Clean",
    *,
    stock_pressure: int = 0,
    target_usd_rate: Optional[float] = None,
    base_usd_rate: Optional[float] = None,
) -> Dict[str, Any]:
    lookup_key = f"{model.strip()} {capacity.strip()}"

    t_usd, b_usd = _load_market_usd_rates()
    t_rate = target_usd_rate if target_usd_rate is not None else t_usd
    b_rate = base_usd_rate if base_usd_rate is not None else b_usd

    # Rule 1: Series 11, 12, 13 unregistered -> reject per Danifon policy
    is_older_series = any(s in model for s in ["11", "12", "13"]) and not any(s in model for s in ["14", "15", "16", "17"])
    is_unregistered = str(register).lower() in ["unregistered", "بدون رجیستر", "بدون کد"]
    if is_older_series and is_unregistered:
        return {
            "success": False,
            "error": "متاسفانه ما گوشیهای سری 13 و پایینتر را در صورتی که رجیستر نباشند، خریداری نمیکنیم.",
            "lookup_key": lookup_key,
        }

    # Rule 2: Empirical benchmark lookup from Knowledge Base
    kb_rec = _find_kb_record(model, capacity, register)
    if kb_rec:
        if kb_rec.get("buy_price"):
            base_buy = int(kb_rec["buy_price"])
        else:
            base_buy = int(kb_rec["sell_price"]) - _fixed_margin(int(kb_rec["sell_price"]))

        batt_match = re.search(r"\d+", str(kb_rec.get("battery", "85")))
        kb_batt = int(batt_match.group(0)) if batt_match else 85
        raw_batt_adj = round((battery - kb_batt) * 350_000)
        battery_adj = min(raw_batt_adj, 2_500_000) if raw_batt_adj > 0 else raw_batt_adj
        condition_adj = CONDITION_SCORES.get(condition, 0)
        hardware_depr = _compute_hardware_depreciation(base_buy, condition)

        register_deduction = 0
        kb_reg_unreg = str(kb_rec.get("register", "")).lower() in ["ندارد", "unregistered", "بدون کد"]

        if str(register).lower() in ["nationalid", "مصوبه کد ملی"]:
            register_deduction = 16_000_000
            if kb_reg_unreg:
                base_buy += _get_customs_duty_for_model(model)
        elif is_unregistered:
            if not kb_reg_unreg:
                register_deduction = _get_registry_fee_for_model(model)
        else:
            if kb_reg_unreg:
                base_buy += _get_customs_duty_for_model(model)

        raw_buy = max(round(base_buy + battery_adj + condition_adj - register_deduction - hardware_depr), 0)
        usd_adj = _compute_usd_adjustment(raw_buy, target_usd_rate=t_rate, base_usd_rate=b_rate)
        buy_price = max(round(raw_buy + usd_adj), 0)
        sell_price = buy_price + _fixed_margin(buy_price)
        buy_min, buy_max, buy_range_str = format_5m_range(buy_price)

        breakdown = {
            "source":             "Knowledge Base Empirical Benchmark",
            "kb_ref_notes":       kb_rec.get("notes", ""),
            "kb_ref_battery":     kb_batt,
            "base_buy_price":     _fmt(base_buy),
            "battery":            battery,
            "battery_adj":        _fmt(battery_adj),
            "condition":          condition,
            "hardware_depr":      _fmt(int(hardware_depr)),
            "register":           register,
            "register_deduction": _fmt(register_deduction),
            "usd_adj":            _fmt(int(usd_adj)),
            "fixed_margin":       _fmt(_fixed_margin(buy_price)),
            "buy_min":            buy_min,
            "buy_max":            buy_max,
            "buy_range_str":      buy_range_str,
        }

        return {
            "success":       True,
            "mp":            sell_price,
            "sell_price":    sell_price,
            "buy_price":     buy_price,
            "buy_min":       buy_min,
            "buy_max":       buy_max,
            "buy_range_str": buy_range_str,
            "breakdown":     breakdown,
            "lookup_key":    lookup_key,
        }

    # Rule 3: Fallback calculation when no KB record exists
    try:
        mp_table = _load_mp_table()
        mp, error, lookup_key = _lookup_mp(model, capacity, mp_table)
        if error is not None:
            return {"success": False, "error": error, "lookup_key": lookup_key}

        tier = _classify_tier(model)
        condition_score = CONDITION_SCORES.get(condition, 0)
        batt_coef = OLDER_BATTERY_COEF if tier == "older" else BATTERY_COEF
        battery_adj = round((battery - 100) * mp * batt_coef)

        register_deduction = 0
        if str(register).lower() in ["nationalid", "مصوبه کد ملی"]:
            register_deduction = 16_000_000
        elif is_unregistered:
            register_deduction = _get_registry_fee_for_model(model)

        # Used market depreciation from Akband
        depr = 0.10 if tier in ["flagship", "pro"] else 0.15
        base_used = round(mp * (1 - depr + 0.01 * stock_pressure))
        raw_used = max(round(base_used + condition_score - register_deduction + battery_adj), 0)
        raw_buy = max(raw_used - _fixed_margin(raw_used), 0)
        usd_adj = _compute_usd_adjustment(raw_buy, target_usd_rate=t_rate, base_usd_rate=b_rate)
        buy_price = max(round(raw_buy + usd_adj), 0)
        sell_price = buy_price + _fixed_margin(buy_price)
        buy_min, buy_max, buy_range_str = format_5m_range(buy_price)

        breakdown = {
            "source":             "Market Table Akband Calculation",
            "mp":                 _fmt(mp),
            "tier":               tier,
            "condition":          condition,
            "condition_adj":      _fmt(condition_score),
            "battery":            battery,
            "battery_adj":        _fmt(battery_adj),
            "register":           register,
            "register_deduction": _fmt(register_deduction),
            "usd_adj":            _fmt(int(usd_adj)),
            "fixed_margin":       _fmt(_fixed_margin(buy_price)),
            "buy_min":            buy_min,
            "buy_max":            buy_max,
            "buy_range_str":      buy_range_str,
        }

        return {
            "success":       True,
            "mp":            mp,
            "sell_price":    sell_price,
            "buy_price":     buy_price,
            "buy_min":       buy_min,
            "buy_max":       buy_max,
            "buy_range_str": buy_range_str,
            "breakdown":     breakdown,
            "lookup_key":    lookup_key,
        }
    except Exception as e:
        logger.error(f"Error in fallback pricing calculation: {e}")
        return {
            "success": False,
            "error": f"❌ Error calculating price: {e}",
            "lookup_key": lookup_key,
        }

def query_knowledge_base(model: str) -> str:
    """Searches historical real transactions database for similar phones with strict model matching."""
    if not os.path.exists(KNOWLEDGE_BASE_PATH):
        return "Knowledge base not found."
    try:
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            kb = json.load(f)
            
        def norm(m: str) -> str:
            clean = str(m).lower().replace("iphone", "").replace("نرمال", "").replace("normal", "").strip()
            return re.sub(r"\s+", " ", clean)

        nq = norm(model)
        q_words = set(nq.split())

        exact = []
        partial = []
        for item in kb:
            nm = norm(item.get("model", ""))
            m_words = set(nm.split())

            # Strict qualifier check: pro, max, plus must match
            if ("pro" in q_words) != ("pro" in m_words):
                continue
            if ("max" in q_words) != ("max" in m_words):
                continue
            if ("plus" in q_words) != ("plus" in m_words):
                continue

            if nm == nq:
                exact.append(item)
            elif nm in nq or nq in nm:
                partial.append(item)

        results = exact or partial
        if not results:
            return "هیچ دیتای تاریخی برای این مدل در دیتابیس یافت نشد."
            
        return json.dumps(results[:5], ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return str(e)

def get_market_context() -> str:
    """Retrieves live USD rate and market condition notes."""
    try:
        if os.path.exists(MARKET_CONTEXT_PATH):
            with open(MARKET_CONTEXT_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return json.dumps({"usd_rate": 0, "market_condition": "عادی"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error reading market context: {e}")
        return json.dumps({"error": str(e)})

def update_market_prices(prices_json: str, usd_rate: float, market_condition: str) -> str:
    """Updates mp_table.json and market_context.json safely."""
    try:
        mp = _load_mp_table()
        new_prices = json.loads(prices_json)
        
        for model, price_map in new_prices.items():
            if isinstance(price_map, dict):
                if model not in mp:
                    mp[model] = {}
                mp[model].update(price_map)
            else:
                return json.dumps({"error": "prices_json must be a dict of dicts: {model: {capacity: price}}"})
                
        with open(MP_TABLE_PATH, "w", encoding="utf-8") as f:
            json.dump(mp, f, indent=2, ensure_ascii=False)
            
        context = {
            "usd_rate": usd_rate,
            "market_condition": market_condition
        }
        with open(MARKET_CONTEXT_PATH, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
            
        return json.dumps({"success": True, "message": "Market prices and context updated successfully."})
    except Exception as e:
        logger.error(f"Error updating market prices: {e}")
        return json.dumps({"error": str(e)})
