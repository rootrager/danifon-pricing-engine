import logging
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

def escape_markdown(text: str) -> str:
    """Escapes Telegram Markdown special characters in dynamic values."""
    if not text:
        return ""
    for char in ['_', '*', '`', '[']:
        text = text.replace(char, f"\\{char}")
    return text

def send_chunked_message(
    bot: Any,
    chat_id: int,
    text: str,
    reply_markup: Optional[Any] = None,
    parse_mode: Optional[str] = 'HTML'
) -> List[Any]:
    """
    Sends message split into chunks if it exceeds Telegram's 4096-character limit.
    Splits cleanly on line boundaries (\n).
    Only the last chunk contains the reply_markup keyboard.
    If parse_mode fails (e.g. invalid Markdown/HTML entities), automatically retries
    with parse_mode=None (plain text).
    """
    LIMIT = 4096
    
    if len(text) <= LIMIT:
        try:
            return [bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)]
        except Exception as e:
            logger.warning(f"Initial send with parse_mode={parse_mode} failed, trying plain text fallback: {e}")
            if parse_mode is not None:
                try:
                    return [bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=None)]
                except Exception as inner_e:
                    logger.error(f"Fallback plain text failed: {inner_e}")
                    raise inner_e
            else:
                raise e
        
    chunks = []
    current_chunk = ""
    lines = text.split("\n")
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 > LIMIT:
            if current_chunk:
                chunks.append(current_chunk.strip("\n"))
                current_chunk = line + "\n"
            else:
                forced_chunks = [line[i:i+LIMIT] for i in range(0, len(line), LIMIT)]
                for fc in forced_chunks[:-1]:
                    chunks.append(fc)
                current_chunk = forced_chunks[-1] + "\n"
        else:
            current_chunk += line + "\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip("\n"))
        
    sent_msgs = []
    for idx, chunk in enumerate(chunks):
        is_last = (idx == len(chunks) - 1)
        markup = reply_markup if is_last else None
        
        try:
            msg = bot.send_message(
                chat_id=chat_id,
                text=chunk,
                reply_markup=markup,
                parse_mode=parse_mode
            )
            sent_msgs.append(msg)
        except Exception as e:
            logger.error(f"Failed to send chunk {idx}: {e}")
            if parse_mode is not None:
                try:
                    msg = bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        reply_markup=markup,
                        parse_mode=None
                    )
                    sent_msgs.append(msg)
                except Exception as inner_e:
                    logger.error(f"Fallback plain text failed for chunk {idx}: {inner_e}")
                    raise inner_e
            else:
                raise e
                
    return sent_msgs
