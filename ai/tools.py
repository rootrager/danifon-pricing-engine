import json
import sys
import os
import logging
from core.config import BASE_DIR, HERMES_AGENT_PATH
from core.security import sanitize_imei, sanitize_amount, sanitize_text
from services import inventory_service, pricing_service, reporting_service

logger = logging.getLogger(__name__)

# --- Safe Hermes Registry Import with Path Isolation ---
_original_path = list(sys.path)
try:
    if HERMES_AGENT_PATH not in sys.path:
        sys.path.insert(0, HERMES_AGENT_PATH)
    venv_site_packages = os.path.join(HERMES_AGENT_PATH, "venv/lib/python3.11/site-packages")
    if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
        sys.path.append(venv_site_packages)
        
    from tools.registry import registry
    _HAS_HERMES = True
except Exception as e:
    logger.warning(f"Could not import Hermes tool registry: {e}")
    registry = None
    _HAS_HERMES = False
finally:
    # Ensure BASE_DIR is restored at the front of sys.path
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

# --- Deterministic Tool Implementations ---

def tool_add_device(imei: str, model: str, buy_price: float, hamta_status: str, condition: str) -> str:
    """
    Adds a new smart device to the store's inventory with validation.
    """
    try:
        clean_imei = sanitize_imei(imei)
        clean_price = sanitize_amount(buy_price)
        clean_model = sanitize_text(model, 100)
        clean_condition = sanitize_text(condition, 250)
        status = "yes" if str(hamta_status).lower() in ["yes", "y", "true", "بله"] else "no"
        
        success = inventory_service.add_smart_device(
            imei=clean_imei,
            model=clean_model,
            buy_price=clean_price,
            hamta_status=status,
            condition_notes=clean_condition
        )
        return json.dumps({"success": success, "imei": clean_imei}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in tool_add_device: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def tool_register_sale(imei: str, sell_price: float, payment_notes: str, is_hamta_done: bool) -> str:
    """
    Registers the sale of an existing device in inventory with validation.
    """
    try:
        clean_imei = sanitize_imei(imei)
        clean_price = sanitize_amount(sell_price)
        status = "yes" if is_hamta_done else "no"
        
        success = inventory_service.sell_smart_device(
            imei=clean_imei,
            sell_price=clean_price,
            hamta_status=status
        )
        return json.dumps({
            "success": success,
            "imei": clean_imei,
            "payment_notes": sanitize_text(payment_notes, 200)
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in tool_register_sale: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def tool_draft_channel_post(imei: str, proposed_price: float, text: str) -> str:
    """
    Drafts a Telegram channel promo post ready for Human-In-The-Loop (HITL) approval.
    """
    try:
        clean_imei = sanitize_text(imei, 30)
        clean_price = sanitize_amount(proposed_price)
        clean_text = sanitize_text(text, 3000)
        
        payload = {
            "action": "channel_draft",
            "imei": clean_imei,
            "proposed_price": clean_price,
            "text": clean_text
        }
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def tool_get_report() -> str:
    """
    Retrieves financial metrics and pending Hamta transfers from reporting service.
    """
    try:
        dash = reporting_service.get_financial_dashboard()
        pending = reporting_service.get_pending_hamta_transfers()
        report = {
            "dashboard": {
                "in_stock_count": dash["in_stock_count"],
                "sold_count": dash["sold_count"],
                "revenue": dash["total_revenue"],
                "profit": dash["total_profit"]
            },
            "pending_hamta": [
                {"imei": r["id"], "model": r["name"], "hamta_status": r["status"], "timestamp": r["date"]}
                for r in pending["smart"] + pending["legacy"]
            ]
        }
        return json.dumps(report, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error in tool_get_report: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

def tool_search_inventory(query: str) -> str:
    """
    Searches the database to find device IMEI and records matching query.
    """
    try:
        return inventory_service.search_devices(query)
    except Exception as e:
        logger.error(f"Error in tool_search_inventory: {e}")
        return str(e)

def tool_get_market_price(model: str) -> str:
    """
    Searches base prices in mp_table for a given model.
    """
    try:
        mp = pricing_service._load_mp_table()
        res = {}
        for k, v in mp.items():
            if model.lower().strip() in k.lower().strip():
                res[k] = v
        return json.dumps(res, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def tool_get_registry_fees() -> str:
    """
    Returns the table of customs/registry fees.
    """
    return json.dumps(pricing_service.REGISTRY_FEES, ensure_ascii=False)

def tool_update_market_prices(prices_json: str, usd_rate: float, market_condition: str) -> str:
    """
    Updates the market prices database and current market context.
    """
    try:
        rate = sanitize_amount(usd_rate)
        condition = sanitize_text(market_condition, 200)
        return pricing_service.update_market_prices(prices_json, rate, condition)
    except Exception as e:
        return json.dumps({"error": str(e)})

def tool_get_market_context() -> str:
    """
    Retrieves the current USD rate and market condition notes.
    """
    return pricing_service.get_market_context()

def tool_query_knowledge_base(model: str) -> str:
    """
    Queries historical past transactions knowledge base.
    """
    return pricing_service.query_knowledge_base(model)

# --- Register in Hermes Tool Registry if Available ---
if _HAS_HERMES and registry:
    # 1. Admin Agent Toolset
    registry.register(
        name="tool_add_device",
        toolset="admin_agent",
        schema={
            "name": "tool_add_device",
            "description": "Adds a new smart device (e.g. mobile phone) to the store's inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "imei": {"type": "string", "description": "Unique 15-digit IMEI of the device"},
                    "model": {"type": "string", "description": "Model of the device (e.g. 'iPhone 15 Pro')"},
                    "buy_price": {"type": "number", "description": "Purchase price in Tomans"},
                    "hamta_status": {"type": "string", "description": "Registry status in Hamta ('yes' or 'no')"},
                    "condition": {"type": "string", "description": "Condition/battery details"}
                },
                "required": ["imei", "model", "buy_price", "hamta_status", "condition"]
            }
        },
        handler=lambda args, **kw: tool_add_device(
            imei=args.get("imei", ""),
            model=args.get("model", ""),
            buy_price=args.get("buy_price", 0.0),
            hamta_status=args.get("hamta_status", "no"),
            condition=args.get("condition", "")
        ),
        override=True
    )

    registry.register(
        name="tool_register_sale",
        toolset="admin_agent",
        schema={
            "name": "tool_register_sale",
            "description": "Registers the sale of an existing device in inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "imei": {"type": "string", "description": "IMEI of the sold device"},
                    "sell_price": {"type": "number", "description": "Sale price in Tomans"},
                    "payment_notes": {"type": "string", "description": "Notes e.g. paid cash, credit, installment details"},
                    "is_hamta_done": {"type": "boolean", "description": "Whether Hamta transfer is completed"}
                },
                "required": ["imei", "sell_price", "payment_notes", "is_hamta_done"]
            }
        },
        handler=lambda args, **kw: tool_register_sale(
            imei=args.get("imei", ""),
            sell_price=args.get("sell_price", 0.0),
            payment_notes=args.get("payment_notes", ""),
            is_hamta_done=args.get("is_hamta_done", False)
        ),
        override=True
    )

    registry.register(
        name="tool_draft_channel_post",
        toolset="admin_agent",
        schema={
            "name": "tool_draft_channel_post",
            "description": "Drafts a Telegram channel promo post and queues it for admin approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "imei": {"type": "string", "description": "IMEI of the device"},
                    "proposed_price": {"type": "number", "description": "Proposed channel display price"},
                    "text": {"type": "string", "description": "Proposed post caption"}
                },
                "required": ["imei", "proposed_price", "text"]
            }
        },
        handler=lambda args, **kw: tool_draft_channel_post(
            imei=args.get("imei", ""),
            proposed_price=args.get("proposed_price", 0.0),
            text=args.get("text", "")
        ),
        override=True
    )

    registry.register(
        name="tool_get_report",
        toolset="admin_agent",
        schema={
            "name": "tool_get_report",
            "description": "Gets financial report metrics and the list of pending Hamta transfers.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        handler=lambda args, **kw: tool_get_report(),
        override=True
    )

    registry.register(
        name="tool_search_inventory",
        toolset="admin_agent",
        schema={
            "name": "tool_search_inventory",
            "description": "Searches the database to find a device's IMEI based on its name or price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (model name, price, status, or condition notes)"}
                },
                "required": ["query"]
            }
        },
        handler=lambda args, **kw: tool_search_inventory(query=args.get("query", "")),
        override=True
    )

    registry.register(
        name="tool_update_market_prices",
        toolset="admin_agent",
        schema={
            "name": "tool_update_market_prices",
            "description": "Updates the database with daily new phone prices, USD rate, and market condition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prices_json": {"type": "string", "description": "JSON string of format: {'iPhone 16 Pro Max': {'256': 240000000}}"},
                    "usd_rate": {"type": "number", "description": "Current USD rate in Tomans"},
                    "market_condition": {"type": "string", "description": "Notes on market status"}
                },
                "required": ["prices_json", "usd_rate", "market_condition"]
            }
        },
        handler=lambda args, **kw: tool_update_market_prices(
            prices_json=args.get("prices_json", "{}"),
            usd_rate=args.get("usd_rate", 0),
            market_condition=args.get("market_condition", "")
        ),
        override=True
    )

    # 2. Custom Toolset
    registry.register(
        name="tool_get_market_price",
        toolset="custom",
        schema={
            "name": "tool_get_market_price",
            "description": "Searches the updated market pricing base table for a given model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "The iPhone model to look up"}
                },
                "required": ["model"]
            }
        },
        handler=lambda args, **kw: tool_get_market_price(model=args.get("model", "")),
        override=True
    )

    registry.register(
        name="tool_get_registry_fees",
        toolset="custom",
        schema={
            "name": "tool_get_registry_fees",
            "description": "Returns the table of customs/registry fees to deduct if a phone is unregistered.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        handler=lambda args, **kw: tool_get_registry_fees(),
        override=True
    )

    registry.register(
        name="tool_get_market_context",
        toolset="custom",
        schema={
            "name": "tool_get_market_context",
            "description": "Retrieves the current USD rate and market condition notes to adjust pricing strategies.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        handler=lambda args, **kw: tool_get_market_context(),
        override=True
    )

    registry.register(
        name="tool_query_knowledge_base",
        toolset="custom",
        schema={
            "name": "tool_query_knowledge_base",
            "description": "Searches the Danifon historical knowledge base for real past transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "The phone model (e.g. '13 Pro' or '11')"}
                },
                "required": ["model"]
            }
        },
        handler=lambda args, **kw: tool_query_knowledge_base(model=args.get("model", "")),
        override=True
    )
