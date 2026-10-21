# custom_tools.py — Backward-compatible Hermes custom tools wrapper
import json
import logging
from core import database
from services.pricing_service import _load_mp_table, _find_model
from ai.tools import registry, _HAS_HERMES

logger = logging.getLogger(__name__)

def get_market_price(series: str, model: str, capacity: str) -> str:
    """Returns baseline price from mp_table for a given model and capacity."""
    try:
        mp_table = _load_mp_table()
        _, caps = _find_model(model, mp_table)
        if not caps:
            return json.dumps({"error": f"Model {model} not found"})
        cap_clean = "".join(filter(str.isdigit, capacity))
        price = caps.get(cap_clean) or caps.get(capacity)
            
        if price:
            return json.dumps({"model": model, "capacity": capacity, "base_price": price})
        return json.dumps({"error": f"Capacity {capacity} not found for model {model}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_admin_feedback() -> str:
    """Queries the SQLite database for recent admin feedback adjustments."""
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Agent_Action, Admin_Response, Corrected_Data, Timestamp FROM AdminFeedback ORDER BY Feedback_ID DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        
        feedback_list = [
            {
                "agent_action": r[0],
                "admin_response": r[1],
                "corrected_data": r[2],
                "timestamp": r[3]
            }
            for r in rows
        ]
        return json.dumps(feedback_list, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

if _HAS_HERMES and registry:
    registry.register(
        name="get_market_price",
        toolset="custom",
        schema={
            "name": "get_market_price",
            "description": "Returns baseline market price from local price database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "series": {"type": "string"},
                    "model": {"type": "string"},
                    "capacity": {"type": "string"}
                },
                "required": ["series", "model", "capacity"]
            }
        },
        handler=lambda args, **kw: get_market_price(
            series=args.get("series", ""),
            model=args.get("model", ""),
            capacity=args.get("capacity", "")
        ),
        override=True
    )

    registry.register(
        name="get_admin_feedback",
        toolset="custom",
        schema={
            "name": "get_admin_feedback",
            "description": "Queries historical admin feedback corrections.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        handler=lambda args, **kw: get_admin_feedback(),
        override=True
    )
