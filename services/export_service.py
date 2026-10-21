import csv
import os
import sqlite3
import tempfile
import logging
from datetime import datetime
from typing import Tuple
from core.config import DB_PATH
from core.database import get_connection

logger = logging.getLogger(__name__)

def export_tables_to_csv() -> Tuple[str, str]:
    """
    Exports SalesInvoice and InstallmentContracts tables to temporary CSV files.
    Returns a tuple of absolute paths: (sales_csv_path, installments_csv_path).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_date = datetime.now().strftime("%Y-%m-%d")
        temp_dir = tempfile.gettempdir()
        
        sales_path = os.path.join(temp_dir, f"Danifonex_Sales_{now_date}.csv")
        installments_path = os.path.join(temp_dir, f"Danifonex_Installments_{now_date}.csv")
        
        # 1. Export SalesInvoice
        cursor.execute("PRAGMA table_info(SalesInvoice)")
        sales_headers = [info[1] for info in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM SalesInvoice")
        sales_rows = cursor.fetchall()
        
        with open(sales_path, 'w', encoding='utf-8-sig', newline='') as sales_f:
            sales_writer = csv.writer(sales_f)
            sales_writer.writerow(sales_headers)
            sales_writer.writerows(sales_rows)
        
        # 2. Export InstallmentContracts
        cursor.execute("PRAGMA table_info(InstallmentContracts)")
        installments_headers = [info[1] for info in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM InstallmentContracts")
        installments_rows = cursor.fetchall()
        
        with open(installments_path, 'w', encoding='utf-8-sig', newline='') as inst_f:
            installments_writer = csv.writer(inst_f)
            installments_writer.writerow(installments_headers)
            installments_writer.writerows(installments_rows)
            
        return sales_path, installments_path
    finally:
        conn.close()

def get_database_backup_path() -> str:
    """Returns verified path to SQLite database."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")
    return DB_PATH
