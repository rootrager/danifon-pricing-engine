# Phase 4.2 Architecture Migration Report

This report outlines the ERP enhancement extensions added to the Admin Control Panel, including transaction ledgering, gross profit metrics, and Hamta registry tracking.

---

## 1. Database Schema Extensions (`db_manager.py`)
To capture transaction invoices natively, the SQLite schema was expanded with the following table:

*   **`SalesInvoice`**:
    *   `Invoice_ID` (INTEGER PRIMARY KEY AUTOINCREMENT)
    *   `Item_Name` (TEXT)
    *   `Buy_Price` (REAL)
    *   `Sell_Price` (REAL)
    *   `Hamta_Status` (TEXT) -- Limit: 'بله' (Yes), 'خیر' (No)
    *   `Date` (TIMESTAMP)

### Data Helper Methods:
*   `add_sales_invoice(...)`: Inserts sales metadata records into the DB.
*   `get_pending_hamta_transfers()`: Queries all invoices where `Hamta_Status` is recorded as pending ('خیر', 'No', 'False').
*   `get_total_profit()`: Summarizes total store margin using cumulative aggregate metrics (`SUM(Sell_Price - Buy_Price)`).

---

## 2. Admin UI Enhancements (`bot.py`)
Two new buttons were registered under the Admin panel keyboard:
1.  **ثبت فاکتور فروش (Register Sale)**: Kicks off the invoice tracking conversation helper.
2.  **گزارش مالی و همتا (Hamta Report)**: Renders financial audit reports.

---

## 3. Invoice Registration Conversation Handler
A state machine manages the registration steps:
*   `INV_NAME`: Captures device name or model.
*   `INV_BUY`: Validates and records target purchase price.
*   `INV_SELL`: Validates and records final sell price.
*   `INV_HAMTA`: Displays inline buttons to record the registry ownership status ('بله' / 'خیر').
*   **Resolution**: Commits the dataset to SQLite and displays a success confirmation.

---

## 4. Financial & Hamta Reporting
Selecting the reporting panel queries total margins and lists outstanding ownership transfer IDs. The resulting list is packaged and sent to the administrator utilizing the `send_chunked_message` utility, preventing character limit crashes.
