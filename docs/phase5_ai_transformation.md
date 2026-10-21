# Phase 5: AI-Centric Transformation & Autonomous Admin Agent

Phase 5 has successfully migrated the classical rigid, menu-driven Admin control workflows of the Danifonex mobile store bot into an **LLM-driven Agentic Architecture**. The application now utilizes function calling and natural language understanding via the local **Hermes Agent** framework.

## Key Upgrades

### 1. Database Refactoring (IMEI-Centric)
- Introduced a new `SmartDevices` table to track serialized stock instead of raw models:
  ```sql
  CREATE TABLE SmartDevices (
      IMEI TEXT PRIMARY KEY,
      Model TEXT,
      Buy_Price REAL,
      Sell_Price REAL,
      Status TEXT,
      Hamta_Status TEXT,
      Condition_Notes TEXT,
      Timestamp TIMESTAMP
  )
  ```
- Smart device inventory statuses: `'In Stock'`, `'Sold'`, `'Returned'`, and `'Trade-in'`.
- Created robust helper functions in `db_manager.py`:
  - `add_smart_device(...)`
  - `sell_smart_device(...)`
  - `get_pending_hamta()`
  - `get_store_dashboard()`
  - `mark_smart_device_hamta_done(...)`

### 2. Autonomous Agent Tools (`ai_tools.py`)
Four programmatic tools registered under the `admin_agent` toolset:
1. `tool_add_device`: Inserts a new IMEI record to the inventory database.
2. `tool_register_sale`: Updates sales status, sell price, payment notes, and registration.
3. `tool_draft_channel_post`: Formats and captures details for Telegram promo posts.
4. `tool_get_report`: Aggregates legacy and new accounting statistics + lists pending transfers.
5. `tool_search_inventory`: Performs local database queries to dynamically lookup IMEI numbers.

### 3. Agentic Routing Loop (`ai_engine.py`)
- Employs `AIAgent` using `ag/gemini-3-flash`.
- Custom System Instruction enforces Persian conversational speech and prompts for missing data (e.g., IMEI).
- Specifically instructs the agent to query `tool_search_inventory` to find IMEI details prior to registering transactions.
- Imports custom tools dynamically with specialized path isolation.

### 4. Interactive Telegram Bot Integration (`bot.py`)
- Deprecated legacy `sale_reg_conv` (`ConversationHandler`).
- Handled text inputs inside `admin_chat_router` solely for authorized admins (`AUTHORIZED_ADMINS`).
- Added support for Human-In-The-Loop (HITL) approvals on generated channel drafts:
  - If the agent returns a draft structure, the bot presents interactive inline buttons (`✅ تایید و ارسال` and `❌ رد کردن`).
  - Allows immediate channel publishing directly from the admin chat.
