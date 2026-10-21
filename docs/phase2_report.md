# Phase 2 Architecture Migration Report

This report outlines the details of the Message Chunking implementation and the Human-in-the-Loop (HITL) Admin Approval state machine.

---

## 1. Message Chunking Utility (`utils.py`)
To prevent Telegram API crashes when sending storefront inventory tables or messages exceeding the 4096 character limit, a chunking utility has been added.

### Logic Features:
*   Processes text structures, chunking them strictly at newline boundaries (`\n`) to preserve readable format structure and prevent tag splitting.
*   Enforces a character budget strictly at `4096` chars per chunk.
*   Attaches the `reply_markup` (like inline keyboards) strictly and exclusively to the **final chunk**.

---

## 2. HITL Admin Approval State Machine (`bot.py`)
The direct expert contact forwarding model was replaced with an interactive multi-agent HITL Admin Approval workflow.

### Workflow Details:
1.  **Request Generation (`request_admin_approval`)**:
    *   Generates a short UUID mapping (`action_id`) for every incoming pricing request.
    *   Caches the request context inside `context.bot_data['approval_requests']`.
    *   Sends a formatted prompt draft to the `ADMIN_CHAT_ID` with Approve/Modify options.
2.  **Approve Flow (`handle_admin_decision`)**:
    *   Sends confirmation of approved quote and next steps to the target user.
    *   Updates the administrator's display, and clears request cache.
3.  **Modify Flow (`handle_admin_decision` & `receive_admin_feedback`)**:
    *   Triggers state transition to `WAITING_FOR_ADMIN_FEEDBACK`.
    *   Intercepts administrator feedback text and saves the details to SQLite table `AdminFeedback` for Phase 3 training.
    *   Forwards the administrator's corrected guidance directly back to the target user.

---

## 3. Backward Compatibility
All updates are written using standard procedural APIs from `python-telegram-bot` v13.15, avoiding asynchronous methods (`async`/`await`) to run cleanly on synchronous deployment environments.
