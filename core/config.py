import os

# Base directory for the project (points to /main)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Telegram Bot Token ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TELEGRAM_BOT_TOKEN = BOT_TOKEN

# --- Webhook Settings ---
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "https://dummy.host")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# --- Secrets ---
FLASK_SECRET = os.environ.get("FLASK_SECRET", "change-this-secret")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET")

# --- Telegram Chat IDs & Admins ---
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", ""))
AUTHORIZED_ADMINS = []
ADMIN_IDS = AUTHORIZED_ADMINS

# --- Channel & Usernames ---
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-1004295298733")
TARGET_CHANNEL_ID = CHANNEL_ID
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "danikamali")
EXPERT_USERNAME = os.environ.get("EXPERT_USERNAME", "danikamali")

# --- Vision LLM Config ---
VISION_LLM_URL = os.environ.get("VISION_LLM_URL", "http://127.0.0.1:20128/v1/chat/completions")
VISION_LLM_MODEL = os.environ.get("VISION_LLM_MODEL", "antigravity/gemini-3.1-pro-low")
VISION_LLM_FALLBACKS = [
    m.strip() for m in os.environ.get(
        "VISION_LLM_FALLBACKS",
        "antigravity/gemini-3.6-flash-high,antigravity/gemini-3.5-flash-low,antigravity/gemini-3-flash-preview"
    ).split(",") if m.strip()
]

# --- AI LLM Agent Config ---
AI_LLM_MODEL = os.environ.get("AI_LLM_MODEL", "antigravity/gemini-3.5-flash-low")
AI_LLM_FALLBACKS = [
    m.strip() for m in os.environ.get(
        "AI_LLM_FALLBACKS",
        "antigravity/gemini-3.6-flash-high,antigravity/gemini-3.1-pro-low,antigravity/gemini-3-flash-preview"
    ).split(",") if m.strip()
]

# --- Network & Proxy Config ---
NO_PROXY = {"http": None, "https": None}
TELEGRAM_PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", "http://127.0.0.1:10808")
if TELEGRAM_PROXY_URL and TELEGRAM_PROXY_URL.strip():
    TELEGRAM_PROXY = {"http": TELEGRAM_PROXY_URL, "https": TELEGRAM_PROXY_URL}
else:
    TELEGRAM_PROXY = None

# --- File Paths (Resolved Dynamically) ---
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "store_bot.db"))
MP_TABLE_PATH = os.environ.get("MP_TABLE_PATH", os.path.join(BASE_DIR, "mp_table.json"))
MARKET_CONTEXT_PATH = os.environ.get("MARKET_CONTEXT_PATH", os.path.join(BASE_DIR, "market_context.json"))
KNOWLEDGE_BASE_PATH = os.environ.get("KNOWLEDGE_BASE_PATH", os.path.join(BASE_DIR, "data", "knowledge_base.json"))
IPHONE_DIR = os.environ.get("IPHONE_DIR", os.path.join(BASE_DIR, "iphone"))
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", os.path.join(BASE_DIR, "downloads"))
HERMES_AGENT_PATH = os.environ.get("HERMES_AGENT_PATH", os.path.expanduser("~/.hermes/hermes-agent"))

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
