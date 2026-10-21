import logging
from typing import Dict, Any, List, Tuple
from core import database
from services.pricing_service import _fmt

logger = logging.getLogger(__name__)

def get_financial_dashboard() -> Dict[str, Any]:
    """Aggregates legacy sales invoice metrics and serialized SmartDevices metrics."""
    legacy_count = database.get_total_sales_count()
    legacy_revenue = database.get_total_revenue()
    legacy_profit = database.get_total_profit()
    
    smart_db = database.get_store_dashboard()
    
    total_sales_count = legacy_count + smart_db["sold_count"]
    total_revenue = legacy_revenue + smart_db["revenue"]
    total_profit = legacy_profit + smart_db["profit"]
    
    return {
        "total_sales_count": total_sales_count,
        "total_revenue": total_revenue,
        "total_revenue_formatted": _fmt(int(total_revenue)),
        "total_profit": total_profit,
        "total_profit_formatted": _fmt(int(total_profit)),
        "in_stock_count": smart_db["in_stock_count"],
        "sold_count": smart_db["sold_count"]
    }

def get_pending_hamta_transfers() -> Dict[str, List[Dict[str, Any]]]:
    """Returns combined list of pending Hamta transfers from invoices and SmartDevices."""
    legacy_pending = database.get_pending_hamta_transfers()
    smart_pending = database.get_pending_hamta()
    
    legacy_list = [
        {"id": str(r[0]), "name": r[1], "status": r[2], "date": r[3], "type": "invoice"}
        for r in legacy_pending
    ]
    smart_list = [
        {"id": str(r[0]), "name": r[1], "status": r[2], "date": r[3], "type": "smart_device"}
        for r in smart_pending
    ]
    return {
        "legacy": legacy_list,
        "smart": smart_list,
        "total_pending": len(legacy_list) + len(smart_list)
    }

def mark_hamta_completed(identifier: str) -> bool:
    """Marks Hamta completed by checking if identifier is IMEI or Invoice ID."""
    clean_id = str(identifier).strip()
    if len(clean_id) >= 10:
        return database.mark_smart_device_hamta_done(clean_id)
    else:
        try:
            inv_id = int(clean_id)
            return database.mark_hamta_done(inv_id)
        except ValueError:
            return False
