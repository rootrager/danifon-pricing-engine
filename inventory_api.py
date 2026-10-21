import json
"""
Danifon Inventory API - Read-only public endpoint
Port: 5354, protected by X-API-Key header
"""
import sqlite3
import os
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "/root/price_project/main/store_bot.db"
API_KEY = os.environ.get("INVENTORY_API_KEY", "dani2026inv")

app = FastAPI(title="Danifon Inventory API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn

class InventoryItem(BaseModel):
    item_id: str
    type: str
    series: Optional[str] = None
    model: Optional[str] = None
    capacity: Optional[str] = None
    part: Optional[str] = None
    sim: Optional[str] = None
    registry: Optional[str] = None
    battery: Optional[str] = None
    price: Optional[str] = None
    condition: Optional[str] = None
    photo_id: Optional[str] = None

def check_key(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/health")
def health():
    return {"status": "ok", "service": "danifon-inventory-api"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    type: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None),
):
    check_key(x_api_key)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        q = "SELECT * FROM Inventory WHERE 1=1"
        params = []
        if type:
            q += " AND lower(Type) = ?"
            params.append(type.lower())
        if series:
            q += " AND Series LIKE ?"
            params.append(f"%{series}%")
        if model:
            q += " AND Model LIKE ?"
            params.append(f"%{model}%")
        q += " ORDER BY Type, Series, Model"
        cursor.execute(q, params)
        rows = cursor.fetchall()
        return [
            InventoryItem(
                item_id=row["Item_ID"],
                type=row["Type"] or "used",
                series=row["Series"],
                model=row["Model"],
                capacity=row["Capacity"],
                part=row["Part"],
                sim=row["Sim"],
                registry=row["Registry"],
                battery=row["Battery"],
                price=row["Price"],
                condition=row["Condition"],
                photo_id=row["Photo_ID"],
            )
            for row in rows
        ]
    finally:
        conn.close()

@app.get("/api/inventory/summary")
def get_summary(x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        total = cursor.execute("SELECT COUNT(*) FROM Inventory").fetchone()[0]
        cursor.execute("SELECT Type, COUNT(*) as cnt FROM Inventory GROUP BY Type")
        rows = cursor.fetchall()
        return {"total": total, "by_type": {r["Type"]: r["cnt"] for r in rows}}
    finally:
        conn.close()


REGISTRY_FILE = "/root/price_project/main/data/registry_fees.json"

@app.get("/api/registry-fees")
def get_registry_fees():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                fees = json.load(f)
                return {"status": "ok", "fees": fees}
        except Exception as e:
            pass
    return {"status": "ok", "fees": {}}

import urllib.request
import json
from pydantic import BaseModel

class TelegramMessage(BaseModel):
    bot_token: str
    chat_id: str
    text: str

@app.post("/api/telegram-relay")
def telegram_relay(msg: TelegramMessage, x_api_key: Optional[str] = Header(None)):
    check_key(x_api_key)
    url = f"https://api.telegram.org/bot/sendMessage"
    payload = json.dumps({
        "chat_id": msg.chat_id,
        "text": msg.text,
        "parse_mode": "HTML"
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
