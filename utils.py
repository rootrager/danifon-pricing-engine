# utils.py — Root wrapper re-exporting core.utils
from core.utils import escape_markdown, send_chunked_message

__all__ = ["escape_markdown", "send_chunked_message"]
