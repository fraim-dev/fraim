import logging
import sys

# TODO: Consider JSON formatting, this makes it very easy to integrate dashboards, etc.
#       We could then have a reader that renders these log events differently.

def make_logger(name = None, level= logging.INFO, path: str = None, show_logs = False) -> logging.Logger:
    logger = logging.getLogger(name) # Get or create logger instance by name

    logger.setLevel(level) # Set the log level, always overwriting

    # Ensure the logger is fresh by removing all existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Prints logs to standard error
    if show_logs:
        logger.addHandler(stderr_handler(level))

    # Logs to a file relative to a given path, if any
    if path:
        logger.addHandler(_make_file_handler(level, path))

    return logger


def _make_file_handler(level, path):
    handler = logging.FileHandler(path)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    return handler


def stderr_handler(level):
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    return handler
