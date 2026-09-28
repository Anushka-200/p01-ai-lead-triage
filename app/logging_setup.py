"""One JSON object per log line, safe for many concurrent requests within this process.

Python's logging module serializes every emit() with an internal lock, so log lines from
parallel background workers never interleave or corrupt each other - no extra code needed for
that. What we DO add: a consistent JSON shape, a rotating file (so it can't grow forever), and
a small `log_event` helper so call sites stay short and searchable.

Multiple SEPARATE processes (e.g. several server instances for redundancy) would need their
own log file each, or a shared log aggregator - the in-process lock above doesn't cover that;
out of scope for this single-process app (see README limitations).
"""

import json
import logging
import logging.handlers
import os
from datetime import UTC, datetime

_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }
        for key, value in vars(record).items():
            if key not in _RESERVED:
                payload[key] = value  # our extra=... fields, e.g. message_id, reason
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(
    log_dir: str = "logs", filename: str = "app.jsonl", level: int = logging.INFO
) -> None:
    """Call once, at process startup (the webhook server, or a CLI's main())."""
    root = logging.getLogger()
    if root.handlers:  # already configured - avoid duplicate handlers on re-import/reload
        return
    root.setLevel(level)
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, filename), maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)
    console = logging.StreamHandler()
    console.setFormatter(JsonFormatter())
    root.addHandler(console)

    # Attaching handlers to the ROOT logger means every third-party library's own logger
    # flows through it too. LiteLLM in particular logs chatty, non-JSON internal messages at
    # INFO level that would otherwise break the "one clean JSON object per line" promise.
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)


def log_event(logger: logging.Logger, level: int, event: str, **fields) -> None:
    """logger.info-with-structure: log_event(log, logging.INFO, 'message_registered', message_id=42, action='new')"""
    logger.log(level, event, extra=fields)
