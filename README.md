# 📱 DaniFone iPhone Pricing & Valuation Engine

An intelligent, rule-based valuation and pricing platform tailored for the Apple iPhone secondary and retail market in Iran. Integrates automated Telegram bot channels, inventory management REST APIs, and Vision LLM hardware diagnostics.

---

## 🌟 Key Features

- **Valuation Logic Engine**: Calculates accurate buy/sell quotes based on market base prices, battery health degradation, storage tiers, color demand, and customs/registry status.
- **Vision LLM Image Matching**: Automatically identifies iPhone models, generation, and colorways from user-submitted photos using vision intelligence.
- **Telegram Bot & Channel Automation**: Auto-formats daily market rates, formats broadcast posts for retail channels, and handles interactive quotes.
- **Inventory REST API**: Lightweight Flask API providing endpoints for inventory checks, real-time price lookup, and automated stock feeds.
- **Strict Separation of Trade Rules**: Explicit distinctions between vitrine/retail prices (آکبند/کددار) and consumer buy-in prices (خرید از مشتری).

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Bot Framework**: `python-telegram-bot`
- **Web & API**: Flask, Flask-CORS
- **Image Processing**: Pillow, OpenCV / NumPy
- **Database**: SQLite3 / JSON market configuration tables

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/rootrager/danifon-pricing-engine.git
cd danifon-pricing-engine

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Running the Services
- **Run the Telegram Bot**:
  ```bash
  python run_bot.py
  ```
- **Run the Inventory API Service**:
  ```bash
  python inventory_api.py
  ```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
