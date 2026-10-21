import logging
from typing import Dict, Any, List, Tuple, Optional
from core import database
from core.security import sanitize_imei, sanitize_amount, sanitize_text

logger = logging.getLogger(__name__)

def add_smart_device(
    imei: str,
    model: str,
    buy_price: float,
    hamta_status: str,
    condition_notes: str
) -> bool:
    """Adds or updates a serialized device in stock with validation."""
    clean_imei = sanitize_imei(imei)
    clean_model = sanitize_text(model, 100)
    clean_price = sanitize_amount(buy_price)
    clean_hamta = "yes" if str(hamta_status).lower() in ["yes", "y", "true", "بله"] else "no"
    clean_condition = sanitize_text(condition_notes, 250)
    
    return database.add_smart_device(
        imei=clean_imei,
        model=clean_model,
        buy_price=clean_price,
        hamta_status=clean_hamta,
        condition_notes=clean_condition
    )

def sell_smart_device(
    imei: str,
    sell_price: float,
    hamta_status: str
) -> bool:
    """Registers the sale of a device with validation."""
    clean_imei = sanitize_imei(imei)
    clean_price = sanitize_amount(sell_price)
    clean_hamta = "yes" if str(hamta_status).lower() in ["yes", "y", "true", "بله"] else "no"
    
    return database.sell_smart_device(
        imei=clean_imei,
        sell_price=clean_price,
        hamta_status=clean_hamta
    )

def search_devices(query: str) -> str:
    """Searches SmartDevices in database."""
    clean_query = sanitize_text(query, 100)
    return database.search_devices(clean_query)

def get_storefront_inventory() -> Dict[str, Dict[str, Any]]:
    """Returns grouped inventory: {'new': {...}, 'used': {...}}."""
    return database.get_inventory()

def add_storefront_item(
    item_id: str,
    item_type: str,
    series: str,
    model: str,
    capacity: str,
    part: str,
    sim: str,
    registry: str,
    battery: str,
    price: str,
    condition: str,
    photo_id: str
) -> None:
    """Adds a storefront catalog item."""
    database.add_inventory(
        item_id=item_id,
        item_type=item_type,
        series=series,
        model=model,
        capacity=capacity,
        part=part,
        sim=sim,
        registry=registry,
        battery=battery,
        price=price,
        condition=condition,
        photo_id=photo_id
    )

def remove_storefront_item(item_id: str) -> None:
    """Removes a storefront item by ID."""
    database.remove_inventory(item_id)

def update_storefront_field(item_id: str, field: str, value: str) -> None:
    """Updates a single field on a storefront catalog item."""
    database.update_inventory_field(item_id, field, value)
