import logging
import os
import json
from datetime import datetime

_loggers = {}

def setup_prompt_logger(session_id=None):
    """
    Initializes and returns a logger for capturing prompts.
    Reuses existing logger if already initialized for this session.
    """
    if session_id in _loggers:
        return _loggers[session_id]

    os.makedirs("logs", exist_ok=True)
    session_id = session_id or datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    log_file = f"logs/prompts_{session_id}.log"

    logger = logging.getLogger(f"prompt_logger_{session_id}")
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers if the logger already exists
    if not logger.handlers:
        handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[session_id] = logger
    return logger

def log_prompt(logger, persona, role, content):
    """
    Logs a single prompt entry to the file.
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "persona": persona,
        "role": role,
        "content": content
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
