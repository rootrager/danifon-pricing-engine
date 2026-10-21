# Phase 1 Architecture Migration Report

This report outlines the details of the database migration, architectural cleanup, proxy configurations, and deprecated infrastructure of the Telegram Store Bot project.

---

## 1. Database Migration Status

### SQLite Database: `store_bot.db`
All flat-file JSON inventory records and plain CSV customer logs have been compiled and migrated into a unified transactional relational schema under a local SQLite database (`store_bot.db`).

### Schema Definition
*   **`Users`**:
    *   `User_ID` (INTEGER PRIMARY KEY)
    *   `Username` (TEXT)
    *   `First_Name` (TEXT)
    *   `Phone_Number` (TEXT)
    *   `Date_Joined` (TIMESTAMP)
*   **`Inventory`**:
    *   `Item_ID` (TEXT PRIMARY KEY)
    *   `Type` (TEXT) -- "new" or "used"
    *   `Series` (TEXT)
    *   `Model` (TEXT)
    *   `Capacity` (TEXT)
    *   `Part` (TEXT)
    *   `Sim` (TEXT)
    *   `Registry` (TEXT)
    *   `Battery` (TEXT)
    *   `Price` (TEXT)
    *   `Condition` (TEXT)
    *   `Photo_ID` (TEXT)
*   **`Orders`**:
    *   `Order_ID` (INTEGER PRIMARY KEY AUTOINCREMENT)
    *   `User_ID` (INTEGER, FOREIGN KEY → Users)
    *   `Item_ID` (TEXT, FOREIGN KEY → Inventory)
    *   `Status` (TEXT)
    *   `Timestamp` (TIMESTAMP)
*   **`AdminFeedback`**:
    *   `Feedback_ID` (INTEGER PRIMARY KEY AUTOINCREMENT)
    *   `Agent_Action` (TEXT)
    *   `Admin_Response` (TEXT)
    *   `Corrected_Data` (TEXT)
    *   `Timestamp` (TIMESTAMP)

---

## 2. Long Polling & Proxy Configuration

1.  **Long Polling (`run_bot.py`)**:
    *   Flask server (`app.py`) is fully deprecated.
    *   Bot executes using python-telegram-bot's native long polling engine (`Updater.start_polling()`).
2.  **Strict Proxy Enforcements**:
    *   All outbound Telegram API requests routed via `Updater` are strictly tunnelled through the local HTTP proxy at `http://127.0.0.1:10808` via initialization parameter `request_kwargs={'proxy_url': 'http://127.0.0.1:10808'}`.

---

## 3. Deprecated Components

*   **`database.json`**: Deprecated.
*   **`customer_leads.csv`**: Deprecated.
*   **`app.py`**: Deprecated (No longer hosting HTTP webhook routes).
*   **`inventory_mock.py`**: Deprecated (Sample dictionary mocks).

---

## 4. Refactoring & Bug Fixes

1.  **Removal State Mismatch Fix**:
    *   Deleting inventory items now correctly maps to the SQLite operation `db_manager.remove_inventory()` instead of removing entries from in-memory dictionary lists or JSON structures.
2.  **Environment-driven configurations**:
    *   `ADMIN_CHAT_ID` now respects `os.environ.get("ADMIN_CHAT_ID")` and fallback defaults, preventing environment configuration drift.
3.  **Thread Safe Concurrency**:
    *   Concurrency write faults are resolved by routing transactional mutations to the SQLite database with proper thread isolation.
