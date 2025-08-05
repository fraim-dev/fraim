import logging
import sys
from pathlib import Path

# TODO: Consider JSON formatting, this makes it very easy to integrate dashboards, etc.
#       We could then have a reader that renders these log events differently.


def make_logger(
    name: str | None = None, level: int = logging.INFO, path: str | None = None, show_logs: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)  # Get or create logger instance by name

    logger.setLevel(level)  # Set the log level, always overwriting

    # Ensure the logger is fresh by removing all existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Prints logs to standard error
    if show_logs:
        logger.addHandler(stderr_handler(level))

    # Logs to a file relative to a given path, if any
    if path:
        logger.addHandler(file_handler(level, path))

    return logger


def file_handler(level: int, path: str) -> logging.FileHandler:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    return handler


def stderr_handler(level: int) -> logging.StreamHandler:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    return handler
