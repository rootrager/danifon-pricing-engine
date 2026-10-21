# Phase 4.3 Architecture Migration Report

This report outlines the structural additions supporting programmatic dataset backups in CSV layout and automated alerts scheduled using python-telegram-bot's JobQueue.

---

## 1. CSV Data Export Engine (`export.py`)
To allow administrators to pull structural backups, a dynamic SQL-to-CSV compilation utility was written:
*   Extracts column schemas (`PRAGMA table_info`) and entries from SQLite tables `SalesInvoice` and `InstallmentContracts`.
*   Writes records into temporary files utilizing Python's built-in `tempfile.NamedTemporaryFile` and `csv.writer`.
*   Returns absolute file system references.

---

## 2. Admin Export Callback Integration (`bot.py`)
*   Added the action button "📥 دریافت بک‌آپ اطلاعات (CSV)" to the admin menu interface.
*   Triggers the callback handler `admin_download_csv_backup()`:
    1.  Calls `export_tables_to_csv()` to generate the temporary files.
    2.  Sends the `.csv` documents back to the administrator using `context.bot.send_document()`.
    3.  Deletes the temporary files using `os.remove()` to prevent local server storage clutter.

---

## 3. Automated Daily Reminders (JobQueue)
The Telegram bot long-polling daemon was enhanced to schedule autonomous alerts:
*   **Daily Job Registration (`run_bot.py`)**:
    *   Registers a recurring job with the `Updater.job_queue` using `job_queue.run_daily(..., time=datetime.time(hour=10, minute=0, second=0))`.
*   **Job Logic (`bot.py` -> `daily_hamta_reminder`)**:
    *   Queries `get_pending_hamta_transfers()`. If pending registry ownership changes are present, compiles them and dispatches warning alerts to the designated `ADMIN_CHAT_ID`.
    *   Uses `send_chunked_message` to prevent character limit errors on long transfer queues.
