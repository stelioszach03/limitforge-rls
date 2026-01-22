import sys
import json
import logging
from datetime import timezone
from loguru import logger as _logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except Exception:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _json_sink(message):
    record = message.record
    # Force UTC ISO 8601 timestamp with Z suffix
    ts = record["time"].astimezone(timezone.utc).isoformat()
    payload = {
        "time": ts,
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "extra": record.get("extra", {}),
    }
    if record.get("exception"):
        payload["exception"] = str(record["exception"])  # short representation
    print(json.dumps(payload, ensure_ascii=False), file=sys.stdout)


def setup_logging() -> None:
    level = settings.LOG_LEVEL.upper()

    # Configure Loguru
    _logger.remove()
    _logger.add(
        _json_sink,
        level=level,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    # Intercept standard logging and uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
        logging_logger.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.handlers = [InterceptHandler()]
    root_logger.setLevel(level)


def get_logger(name: str):
    return _logger.bind(logger=name)
