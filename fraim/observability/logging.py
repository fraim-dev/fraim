import logging
import sys
from pathlib import Path


def setup_logging(level: int = logging.INFO, path: str | None = None, show_logs: bool = False) -> None:
    """Configures the root logger for the application."""

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
