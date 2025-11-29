"""Logging configuration for the application."""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from app.config import get_settings

settings = get_settings()


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages toward loguru."""
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record.
        
        Args:
            record: The log record to emit.
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
            
        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
            
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure logging with loguru."""
    # Create logs directory if it doesn't exist
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure loguru
    logger.remove()  # Remove default handler
    
    # Add file handler
    logger.add(
        log_file,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        level=settings.LOG_LEVEL,
        format=format_record,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=format_record,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Disable noisy loggers
    for _log in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "httpx",
        "httpcore",
    ]:
        logging.getLogger(_log).handlers = []
        logging.getLogger(_log).propagate = False
    
    logger.info("Logging configured")


def format_record(record: Dict[str, Any]) -> str:
    """Format log record as JSON."""
    log_record = {
        "timestamp": datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc).isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "name": record["name"],
        "function": record["function"],
        "line": record["line"],
        "correlation_id": record["extra"].get("correlation_id", ""),
        "agent_name": record["extra"].get("agent_name", ""),
        "tool_name": record["extra"].get("tool_name", ""),
    }
    
    # Add exception info if present
    if record["exception"] is not None:
        log_record["exception"] = {
            "type": str(record["exception"].type),
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback.format_exc(),
        }
    
    return json.dumps(log_record, ensure_ascii=False)


def get_logger(name: Optional[str] = None) -> logger:
    """Get a logger with the given name.
    
    Args:
        name: The name of the logger. If None, returns the root logger.
        
    Returns:
        A configured logger instance.
    """
    if name is None:
        name = __name__.split(".")[0]
    return logger.bind(name=name)
