# Phase 4.1 Architecture Migration Report

This report outlines the modifications introduced to support structural financial tracking and the customer installment calculation engine.

---

## 1. Database Expansion Schema (`db_manager.py`)
To enable transaction ledger tracking and deferred payments logs, two new tables have been appended:

1.  **`Accounting`**:
    *   `Record_ID` (INTEGER PRIMARY KEY AUTOINCREMENT)
    *   `Type` (TEXT) -- Limit: 'Sale', 'Expense', 'Return'
    *   `Amount` (REAL)
    *   `Description` (TEXT)
    *   `Date` (TIMESTAMP)
2.  **`InstallmentContracts`**:
    *   `Contract_ID` (INTEGER PRIMARY KEY AUTOINCREMENT)
    *   `User_ID` (INTEGER, FOREIGN KEY → Users)
    *   `Total_Amount` (REAL)
    *   `Months` (INTEGER)
    *   `Monthly_Payment` (REAL)
    *   `Status` (TEXT)
    *   `Date` (TIMESTAMP)

---

## 2. Finance Calculation Logic (`finance.py`)
A mathematical module was written to evaluate credit check terms based on the user's specific store guidelines:

*   **Principal Upgrade fee**: Adds a flat 10% fee (`base_with_fee = principal * 1.10`).
*   **Monthly Interest**: Accumulates 5% interest of the upgraded principal base per month (`monthly_interest = base_with_fee * 0.05`).
*   **Total Payback calculation**: Sums the base with fee and the product of monthly interest and months.
*   **Payment Check amount**: Computes the monthly payload (`total_payback / months`).

---

## 3. Bot Customer Interaction (`bot.py`)
1.  **Menu Registration**:
    *   Appended the button "📊 محاسبه اقساط (Installment Calculator)" to the main menu.
2.  **Conversation Handler (`installment_conv`)**:
    *   `CALC_AMOUNT`: Prompts for loan request up to 50,000,000 Tomans.
    *   `CALC_MONTHS`: Prompts for payback duration options (3, 6, 9, 12 months).
    *   **Resolution**: Computes the details using `finance.py`, records the installment contract in the SQLite database, and returns the breakdown in a clean format to the customer.
