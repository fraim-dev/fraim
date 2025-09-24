import logging
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO, path: str | None = None, show_logs: bool = False) -> None:
    """
    Configures the root logger for the application.

    Args:
        level (int): The logging level (e.g., `logging.INFO`, `logging.DEBUG`, etc)
                     Determines the minimum severity of messages to log.

        path (str | None): The file path where logs should be written, if provided.
                           If None, logs are not written to a file.

        show_logs (bool): If True, logs are also written to the console (stderr).

    This function initializes the root logger with a configurable level, log destination,
    and whether logs are displayed in the terminal. If a file path is specified in the
    `path` argument, logs will be written to that file (directories will be created
    if necessary). If `show_logs` is enabled, logs are additionally streamed to the console.
    """

    # Eg. 2025-09-24 02:54:14,123 [INFO] my_app.auth.services: User logged in successfully.
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers: list[logging.Handler] = []
    if show_logs:
        handlers.append(logging.StreamHandler(sys.stderr))

    if path:
        log_path = Path(path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
        force=True,  # Overwrites any existing root logger configuration
    )
