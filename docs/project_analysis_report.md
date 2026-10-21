# Project Analysis Report: Telegram Store Bot

This document details the structure, database schema, architectural compliance, and identified issues for the iPhone Price Estimator / Telegram Store Bot project.

---

## 1. Current Project Structure

The codebase is a Flask and `python-telegram-bot` (v13.x) integration, designed to be lightweight and run synchronously (ideal for hosting environments like PythonAnywhere).

### Files & Roles

*   **`app.py`**:
    *   Acts as the Flask web server and entry point for Webhooks.
    *   Defines endpoints: `/webhook/<token>` (updates processing), `/set_webhook` (registers webhook url with Telegram API), `/webhook_info` (status checks), and `/` (root health-check).
    *   Initializes the `python-telegram-bot` `Bot` and `Dispatcher` objects.
*   **`bot.py`**:
    *   Houses the primary Telegram bot logic, command/message handlers, conversation states, and admin panel commands.
    *   Implements the user pricing conversation (`ConversationHandler` with states `SERIES`, `MODEL`, `CAPACITY`, `REGISTER`, `BATTERY`).
    *   Implements storefront inventory browsing (`storefront_menu`, `show_used_inventory`, `show_new_inventory`).
    *   Implements the admin control panel for adding (`admin_add_item` conversation) and editing/removing items.
*   **`pricing_engine.py`**:
    *   Encapsulates the calculation formulas for calculating the estimated buying and selling price of an iPhone based on market price (`mp_table.json`).
    *   Calculates margins based on phone tier classifications (Flagship, Pro, Mid, Older) and applies deductions for registration state and battery degradation.
*   **`config.py`**:
    *   Retrieves env vars (`BOT_TOKEN`, `WEBHOOK_HOST`, `ADMIN_SECRET`, etc.) and sets static project configuration parameters (Authorized Admin IDs, Target Channel, Expert Username, etc.).
*   **`mp_table.json`**:
    *   Contains the baseline market price reference structure indexed by phone model and storage capacity (e.g., `"iPhone 16 Pro Max": {"256": 240391667}`).
*   **`database.json`**:
    *   Flat-file JSON database containing currently stored inventory records grouped into `"new"` and `"used"`.
*   **`customer_leads.csv`**:
    *   CSV file compiled dynamically as users authenticate with their phone number via `request_contact=True`. Stores user ids, usernames, first names, phone numbers, and join dates.
*   **`inventory_mock.py`**:
    *   A legacy mock file defining sample used/new inventory items, replaced in the main bot execution path by operations on `database.json`.

---

## 2. Database Schema

The project **does not use SQLite**. Instead, it stores persistent states in two local files:

### 1. File Database: `database.json`
Stores the active store inventory.
```json
{
  "new": {
    "new_001": {
      "series": "16",
      "model": "iPhone 16 Pro",
      "capacity": "256GB",
      "part": "ZA",
      "sim": "دو سیمکارت",
      "registry": "رجیستر شده",
      "battery": "N/A",
      "price": "89000000",
      "condition": "Brand New (Not Activated)",
      "photo_id": "AgACAgQ..."
    }
  },
  "used": {
    "used_001": {
      "series": "13",
      "model": "iPhone 13",
      "capacity": "128GB",
      "part": "ZA",
      "sim": "تک سیمکارت",
      "registry": "بدون رجیستر",
      "battery": "84",
      "price": "42000000",
      "condition": "Clean",
      "photo_id": "AgACAgQ..."
    }
  }
}
```

### 2. CSV Table: `customer_leads.csv`
Used to log contact details of incoming users.
*   **Columns**: `User_ID`, `Username`, `First_Name`, `Phone_Number`, `Date_Joined`

---

## 3. Architecture Audit against Golden Architectural Rules

| Golden Architectural Rule | Status | Audit Findings & Details |
| :--- | :--- | :--- |
| **Proxy Configuration** | **FAIL** | There is no configuration or routing setup in `app.py`, `bot.py`, or `config.py` directing Telegram requests through `127.0.0.1:10808`. The system uses standard python-telegram-bot wrappers which inherit default system environment vars or make direct calls. Similarly, no `NO_PROXY` bypass configurations exist. |
| **Message Chunking** | **FAIL** | There is no logic handling message chunking or split rules. If inventory lists or pricing summaries exceed the Telegram limit of 4096 characters, the bot will trigger an API error (`Message is too long`). Additionally, there is no logic ensuring inline keyboards are only attached to the last message slice. |
| **Persistence** | **FAIL** | The system relies strictly on flat files (`database.json` for inventory and `customer_leads.csv` for contact details). **No SQLite database engine (`sqlite3`) is integrated.** |
| **State Machine & HITL** | **PARTIAL** | State machine uses python-telegram-bot's `ConversationHandler` (internally dictionary/memory-based state per chat_id). However, there is **no Human-in-the-loop (HITL) Admin Approval loop** (e.g., inline buttons to approve/modify a user's pricing quote before posting or notifying). Expert quotes are sent directly to `ADMIN_CHAT_ID` without an interaction mechanism. |
| **Hermes Integration** | **FAIL** | There is **no agent integration** in the codebase. Hermes is not imported, initialized, or utilized in the repository, and no custom toolsets are defined or loaded. |

---

## 4. Missing Features & Critical Bugs

1.  **Concurrency & Persistence Issues (Flat Files)**:
    Since Flask handles requests in threads, simultaneous writes to `database.json` or `customer_leads.csv` will lead to file corruption or race conditions (e.g. `save_inventory` completely overwrites the file). The absence of a real transactional DB like SQLite is a critical blocker for production scaling.
2.  **Lack of Proxy Routing**:
    If hosted in environments requiring strict proxying (or local testing setups using the HTTP proxy specified in Hermes' system memory), API requests will fail or bypass the local tunnel.
3.  **No Message Chunking**:
    If a generated storefront inventory post (`generate_channel_post`) grows large, the bot will crash with a Telegram API exception.
4.  **Pricing Flow is Disabled (Frozen)**:
    `dispatcher.add_handler(CallbackQueryHandler(freeze_pricing_menu, pattern='^menu_pricing$'))` blocks the main pricing flow. The actual conversation handler listens to `^disabled_menu_pricing$`, making the automatic pricing feature unreachable for users.
5.  **Admin Execute Removal State Mismatch**:
    In `admin_execute_removal`, the deletion removes keys from the mock files `NEW_INVENTORY` and `USED_INVENTORY` instead of updating the state of `database.json`, resulting in an out-of-sync database when items are removed. *(Note: While some code patches try to edit this, the definition of `admin_execute_removal` in the file still contains code referencing the mock file, which is a structural mismatch).*
6.  **Hardcoded and Missing Environment Defaults**:
    `ADMIN_CHAT_ID` is hardcoded to `-5544060808` instead of being read dynamically from the environment config, which hinders multi-environment deployments.
