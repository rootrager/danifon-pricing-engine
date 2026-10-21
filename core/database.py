import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from core.config import DB_PATH

logger = logging.getLogger(__name__)

def get_connection() -> sqlite3.Connection:
    """
    Returns a hardened SQLite connection with WAL mode, busy timeout,
    and foreign key enforcement enabled.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn

def init_db() -> None:
    """Initialize all tables in SQLite schema."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            User_ID INTEGER PRIMARY KEY,
            Username TEXT,
            First_Name TEXT,
            Phone_Number TEXT,
            Date_Joined TIMESTAMP
        )
        """)
        
        # 2. Inventory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Inventory (
            Item_ID TEXT PRIMARY KEY,
            Type TEXT,
            Series TEXT,
            Model TEXT,
            Capacity TEXT,
            Part TEXT,
            Sim TEXT,
            Registry TEXT,
            Battery TEXT,
            Price TEXT,
            Condition TEXT,
            Photo_ID TEXT
        )
        """)
        
        # 3. Orders table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            Order_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER,
            Item_ID TEXT,
            Status TEXT,
            Timestamp TIMESTAMP,
            FOREIGN KEY(User_ID) REFERENCES Users(User_ID),
            FOREIGN KEY(Item_ID) REFERENCES Inventory(Item_ID)
        )
        """)
        
        # 4. AdminFeedback table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS AdminFeedback (
            Feedback_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Agent_Action TEXT,
            Admin_Response TEXT,
            Corrected_Data TEXT,
            Timestamp TIMESTAMP
        )
        """)
        
        # 5. Accounting table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Accounting (
            Record_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Type TEXT,
            Amount REAL,
            Description TEXT,
            Date TIMESTAMP
        )
        """)
        
        # 6. InstallmentContracts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS InstallmentContracts (
            Contract_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER,
            Total_Amount REAL,
            Months INTEGER,
            Monthly_Payment REAL,
            Status TEXT,
            Date TIMESTAMP,
            FOREIGN KEY(User_ID) REFERENCES Users(User_ID)
        )
        """)
        
        # 7. SalesInvoice table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SalesInvoice (
            Invoice_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Item_Name TEXT,
            Buy_Price REAL,
            Sell_Price REAL,
            Hamta_Status TEXT,
            Date TIMESTAMP
        )
        """)
        
        # 8. SmartDevices table (IMEI-Centric)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SmartDevices (
            IMEI TEXT PRIMARY KEY,
            Model TEXT,
            Buy_Price REAL,
            Sell_Price REAL,
            Status TEXT,
            Hamta_Status TEXT,
            Condition_Notes TEXT,
            Timestamp TIMESTAMP
        )
        """)

        # 9. StoryDrafts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StoryDrafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            image_path TEXT,
            original_draft TEXT,
            current_draft TEXT,
            status TEXT DEFAULT 'pending_approval',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 10. StoryFeedback table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StoryFeedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id INTEGER,
            admin_id INTEGER,
            feedback_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(draft_id) REFERENCES StoryDrafts(id)
        )
        """)

        # 11. PricingRequests table (HITL Approval Loop)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS PricingRequests (
            request_id TEXT PRIMARY KEY,
            user_id INTEGER,
            user_full_name TEXT,
            username TEXT,
            user_specs_raw TEXT,
            quote_json TEXT,
            status TEXT DEFAULT 'pending',
            final_price INTEGER,
            expert_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
    finally:
        conn.close()

# --- Users Operations ---
def add_user(user_id: int, username: str, first_name: str, phone_number: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Users (User_ID, Username, First_Name, Phone_Number, Date_Joined)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(User_ID) DO UPDATE SET
                Username = excluded.Username,
                First_Name = excluded.First_Name,
                Phone_Number = excluded.Phone_Number,
                Date_Joined = excluded.Date_Joined
        """, (user_id, username, first_name, phone_number, now))
        conn.commit()
    finally:
        conn.close()

# --- Inventory Operations (Legacy format compatibility) ---
def add_inventory(item_id: str, item_type: str, series: str, model: str, capacity: str, part: str, sim: str, registry: str, battery: str, price: str, condition: str, photo_id: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Inventory (Item_ID, Type, Series, Model, Capacity, Part, Sim, Registry, Battery, Price, Condition, Photo_ID)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(Item_ID) DO UPDATE SET
                Type = excluded.Type,
                Series = excluded.Series,
                Model = excluded.Model,
                Capacity = excluded.Capacity,
                Part = excluded.Part,
                Sim = excluded.Sim,
                Registry = excluded.Registry,
                Battery = excluded.Battery,
                Price = excluded.Price,
                Condition = excluded.Condition,
                Photo_ID = excluded.Photo_ID
        """, (item_id, item_type, series, model, capacity, part, sim, registry, battery, price, condition, photo_id))
        conn.commit()
    finally:
        conn.close()

def remove_inventory(item_id: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Inventory WHERE Item_ID = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()

def get_inventory() -> Dict[str, Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Inventory")
        rows = cursor.fetchall()
        
        inventory = {"new": {}, "used": {}}
        for row in rows:
            item_id, item_type, series, model, capacity, part, sim, registry, battery, price, condition, photo_id = row
            item_dict = {
                "series": series,
                "model": model,
                "capacity": capacity,
                "part": part,
                "sim": sim,
                "registry": registry,
                "battery": battery,
                "price": price,
                "condition": condition,
                "photo_id": photo_id
            }
            t = item_type.lower() if item_type else "used"
            if t not in ["new", "used"]:
                t = "used"
            inventory[t][item_id] = item_dict
        return inventory
    finally:
        conn.close()

def update_inventory_field(item_id: str, field: str, value: str) -> None:
    field_mapping = {
        "price": "Price",
        "battery": "Battery",
        "registry": "Registry",
        "sim": "Sim"
    }
    db_column = field_mapping.get(field.lower())
    if not db_column:
        raise ValueError(f"Invalid field to update: {field}")
        
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE Inventory SET {db_column} = ? WHERE Item_ID = ?", (value, item_id))
        conn.commit()
    finally:
        conn.close()

# --- Feedback Operations ---
def add_feedback(agent_action: str, admin_response: str, corrected_data: str = "") -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO AdminFeedback (Agent_Action, Admin_Response, Corrected_Data, Timestamp)
            VALUES (?, ?, ?, ?)
        """, (agent_action, admin_response, corrected_data, now))
        conn.commit()
    finally:
        conn.close()

def get_recent_admin_feedback(limit: int = 10) -> List[Dict[str, Any]]:
    """Queries the SQLite database for recent admin feedback adjustments for AI continuous learning."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Agent_Action, Admin_Response, Corrected_Data, Timestamp
            FROM AdminFeedback
            ORDER BY Feedback_ID DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "agent_action": r[0],
                "admin_response": r[1],
                "corrected_data": r[2],
                "timestamp": r[3]
            })
        return result
    finally:
        conn.close()

# --- Accounting & Invoices ---
def add_accounting_record(record_type: str, amount: float, description: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Accounting (Type, Amount, Description, Date)
            VALUES (?, ?, ?, ?)
        """, (record_type, amount, description, now))
        conn.commit()
    finally:
        conn.close()

def add_installment_contract(user_id: int, total_amount: float, months: int, monthly_payment: float, status: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO InstallmentContracts (User_ID, Total_Amount, Months, Monthly_Payment, Status, Date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, total_amount, months, monthly_payment, status, now))
        conn.commit()
    finally:
        conn.close()

def add_sales_invoice(item_name: str, buy_price: float, sell_price: float, hamta_status: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO SalesInvoice (Item_Name, Buy_Price, Sell_Price, Hamta_Status, Date)
            VALUES (?, ?, ?, ?, ?)
        """, (item_name, buy_price, sell_price, hamta_status, now))
        conn.commit()
    finally:
        conn.close()

def get_pending_hamta_transfers() -> List[Tuple[Any, ...]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Invoice_ID, Item_Name, Hamta_Status, Date FROM SalesInvoice WHERE UPPER(Hamta_Status) IN ('NO', 'خیر', 'FALSE')")
        return cursor.fetchall()
    finally:
        conn.close()

def get_total_profit() -> float:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(Sell_Price - Buy_Price) FROM SalesInvoice")
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0
    finally:
        conn.close()

def get_total_sales_count() -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM SalesInvoice")
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    finally:
        conn.close()

def get_total_revenue() -> float:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(Sell_Price) FROM SalesInvoice")
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0
    finally:
        conn.close()

def mark_hamta_done(invoice_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE SalesInvoice SET Hamta_Status = 'yes' WHERE Invoice_ID = ?", (invoice_id,))
        updated = cursor.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()

# --- SmartDevices (IMEI-Centric) Operations ---
def add_smart_device(imei: str, model: str, buy_price: float, hamta_status: str, condition_notes: str) -> bool:
    """Adds or updates a smart device in inventory safely without destroying existing sell price if sold."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO SmartDevices (IMEI, Model, Buy_Price, Sell_Price, Status, Hamta_Status, Condition_Notes, Timestamp)
            VALUES (?, ?, ?, NULL, 'In Stock', ?, ?, ?)
            ON CONFLICT(IMEI) DO UPDATE SET
                Model = excluded.Model,
                Buy_Price = excluded.Buy_Price,
                Hamta_Status = excluded.Hamta_Status,
                Condition_Notes = excluded.Condition_Notes,
                Timestamp = excluded.Timestamp
        """, (imei, model, buy_price, hamta_status, condition_notes, now))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def sell_smart_device(imei: str, sell_price: float, hamta_status: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE SmartDevices
            SET Sell_Price = ?, Status = 'Sold', Hamta_Status = ?
            WHERE IMEI = ?
        """, (sell_price, hamta_status, imei))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_pending_hamta() -> List[Tuple[Any, ...]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT IMEI, Model, Hamta_Status, Timestamp
            FROM SmartDevices
            WHERE Status = 'Sold' AND UPPER(Hamta_Status) IN ('NO', 'خیر', 'FALSE')
        """)
        return cursor.fetchall()
    finally:
        conn.close()

def mark_smart_device_hamta_done(imei: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE SmartDevices SET Hamta_Status = 'yes' WHERE IMEI = ?", (imei,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_store_dashboard() -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM SmartDevices WHERE Status = 'In Stock'")
        in_stock_count = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM SmartDevices WHERE Status = 'Sold'")
        sold_count = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(Sell_Price) FROM SmartDevices WHERE Status = 'Sold'")
        revenue = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(Sell_Price - Buy_Price) FROM SmartDevices WHERE Status = 'Sold'")
        profit = cursor.fetchone()[0] or 0.0
        
        return {
            "in_stock_count": in_stock_count,
            "sold_count": sold_count,
            "revenue": float(revenue),
            "profit": float(profit)
        }
    finally:
        conn.close()

def search_devices(query: str) -> str:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT IMEI, Model, Buy_Price, Status, Condition_Notes
            FROM SmartDevices
            WHERE Model LIKE ? OR Condition_Notes LIKE ? OR CAST(Buy_Price AS TEXT) LIKE ? OR IMEI LIKE ?
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        rows = cursor.fetchall()
        
        if not rows:
            return "No matching smart devices found in database."
            
        results = []
        for row in rows:
            imei, model, buy_price, status, condition = row
            results.append(
                f"Found: {model}, Buy Price: {buy_price}, Status: {status}, IMEI: {imei}, Condition: {condition}"
            )
        return "\n".join(results)
    finally:
        conn.close()

# --- Story Drafts Operations ---
def save_story_draft(admin_id: int, image_path: str, draft_text: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO StoryDrafts (admin_id, image_path, original_draft, current_draft)
            VALUES (?, ?, ?, ?)
        """, (admin_id, image_path, draft_text, draft_text))
        draft_id = cursor.lastrowid
        conn.commit()
        return draft_id
    finally:
        conn.close()

def update_story_draft(draft_id: int, new_text: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE StoryDrafts SET current_draft = ? WHERE id = ?", (new_text, draft_id))
        conn.commit()
    finally:
        conn.close()

def update_story_draft_status(draft_id: int, status: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE StoryDrafts SET status = ? WHERE id = ?", (status, draft_id))
        conn.commit()
    finally:
        conn.close()

def get_story_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM StoryDrafts WHERE id = ?", (draft_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'admin_id': row[1],
                'image_path': row[2],
                'original_draft': row[3],
                'current_draft': row[4],
                'status': row[5]
            }
        return None
    finally:
        conn.close()

def save_story_feedback(draft_id: int, admin_id: int, feedback_text: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO StoryFeedback (draft_id, admin_id, feedback_text)
            VALUES (?, ?, ?)
        """, (draft_id, admin_id, feedback_text))
        conn.commit()
    finally:
        conn.close()

def get_recent_story_feedback(limit: int = 5) -> List[str]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT feedback_text FROM StoryFeedback 
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()

# --- Pricing Requests Operations (HITL Persistence) ---
def save_pricing_request(request_id: str, user_id: int, user_full_name: str, username: str, user_specs_raw: str, quote_json: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO PricingRequests (request_id, user_id, user_full_name, username, user_specs_raw, quote_json, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (request_id, user_id, user_full_name, username, user_specs_raw, quote_json))
        conn.commit()
    finally:
        conn.close()

def get_pricing_request(request_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT request_id, user_id, user_full_name, username, user_specs_raw, quote_json, status, final_price, expert_notes, created_at FROM PricingRequests WHERE request_id = ?", (request_id,))
        row = cursor.fetchone()
        if row:
            return {
                "request_id": row[0],
                "user_id": row[1],
                "user_full_name": row[2],
                "username": row[3],
                "user_specs_raw": row[4],
                "quote_json": row[5],
                "status": row[6],
                "final_price": row[7],
                "expert_notes": row[8],
                "created_at": row[9]
            }
        return None
    finally:
        conn.close()

def update_pricing_request(request_id: str, status: str, final_price: Optional[int] = None, expert_notes: str = "") -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE PricingRequests
            SET status = ?, final_price = COALESCE(?, final_price), expert_notes = ?
            WHERE request_id = ?
        """, (status, final_price, expert_notes, request_id))
        conn.commit()
    finally:
        conn.close()

# Auto-initialize on import
init_db()

def clear_new_inventory() -> int:
    """Deletes all new/sealed items from the inventory."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Inventory WHERE lower(Type) = ?", ("new",))
        count = cursor.rowcount
        conn.commit()
        return count
    except Exception as e:
        import logging
        logging.error(f"Error clearing new inventory: {e}")
        return 0
    finally:
        conn.close()
