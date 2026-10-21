# Phase 3 Architecture Migration Report

This report outlines the details of the AI Agent Injection, custom tools registration, local proxy configuration, and the integration of the dynamic pricing loop with human-in-the-loop (HITL) validations.

---

## 1. Local LLM Proxy Bypassing Configuration
To prevent programmatic agent execution requests from failing due to external proxy routing:
*   In `ai_engine.py`, `os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"` is set at the absolute top of the module to bypass the shadowsocks tunnel.

---

## 2. Hermes Custom Toolsets (`custom_tools.py`)
Custom tools were written and registered to expose project data structures to the programmatic `AIAgent` core:
1.  **`get_market_price`**:
    *   Finds base pricing inside `mp_table.json` based on the requested model and storage layout.
2.  **`get_admin_feedback`**:
    *   Performs structural reads on the SQLite `AdminFeedback` table, retrieving the last 10 adjustments made by administrators. Allows the model to learn and optimize pricing calculations recursively.

---

## 3. Dynamic Agent Injection (`ai_engine.py`)
Pricing calculations were migrated from static mathematical formulas to an AI-driven agent loop:
*   Initializes the core `AIAgent` utilizing `enabled_toolsets=["custom"]` to restrict tool access strictly to our registered plugins.
*   Enforces systemic guidelines instructing the assistant to evaluate previous feedback logs first, query the current market values, and compute optimized, self-learned quotes.
*   Outputs the response strictly in Persian.

---

## 4. Bot & Integration Flow (`bot.py` & `run_bot.py`)
1.  **Pricing conversation handler update**:
    *   Instead of calling the static formula calculation method directly, the user pricing loop calls `ai_engine.generate_expert_quote()`.
    *   Passes the AI-generated quote proposal directly into `request_admin_approval()` to kick off the HITL Admin verification loop.
2.  **Long Polling Support**:
    *   No changes were introduced to the standard polling pipeline (`run_bot.py`), ensuring backward-compatible v13 stability.
