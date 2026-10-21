import os
import pytest
from services.export_service import export_tables_to_csv, get_database_backup_path

def test_export_tables_to_csv():
    sales_csv, inst_csv = export_tables_to_csv()
    assert os.path.exists(sales_csv)
    assert os.path.exists(inst_csv)
    
    # Read headers
    with open(sales_csv, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        assert len(content) > 0
        
    with open(inst_csv, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        assert len(content) > 0
        
    # Clean up test files
    os.remove(sales_csv)
    os.remove(inst_csv)

def test_get_database_backup_path():
    db_path = get_database_backup_path()
    assert os.path.exists(db_path)
