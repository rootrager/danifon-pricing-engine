# run_bot.py — Telegram Bot Long Polling Entrypoint
import sys, types

# Polyfill for Python 3.13/3.14 and modern urllib3 to prevent PTB v13 crashes
import urllib3
if not hasattr(urllib3, 'contrib'):
    urllib3.contrib = types.ModuleType('urllib3.contrib')
    sys.modules['urllib3.contrib'] = urllib3.contrib

if 'urllib3.contrib.appengine' not in sys.modules:
    appengine_mock = types.ModuleType('urllib3.contrib.appengine')
    appengine_mock.is_appengine = lambda: False
    appengine_mock.is_appengine_sandbox = lambda: False
    sys.modules['urllib3.contrib.appengine'] = appengine_mock
    urllib3.contrib.appengine = appengine_mock

import logging
import os
from telegram.ext import Updater
from config import BOT_TOKEN, TELEGRAM_PROXY_URL
from bot import setup_dispatcher

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in environment or config!")
        sys.exit(1)
        
    request_kwargs = {}
    if TELEGRAM_PROXY_URL and TELEGRAM_PROXY_URL.strip():
        logger.info(f"Initializing bot with Long Polling via proxy {TELEGRAM_PROXY_URL}...")
        request_kwargs['proxy_url'] = TELEGRAM_PROXY_URL
    else:
        logger.info("Initializing bot with Long Polling directly (no proxy)...")
    
    updater = Updater(
        token=BOT_TOKEN,
        use_context=True,
        request_kwargs=request_kwargs
    )
    
    # Setup dispatcher and hand it over to updater
    setup_dispatcher(updater.dispatcher)
    
    # Enforce Webhook Deletion strictly for new token routing
    logger.info("Enforcing webhook deletion for token registry...")
    updater.bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Starting long polling...")
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

if __name__ == "__main__":
    main()
