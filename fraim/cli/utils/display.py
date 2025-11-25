# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Display utilities for CLI commands."""

import io
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, TextIO

from fraim.util import tty


def should_show_rich_display(force_rich_display: bool) -> bool:
    """Determine whether to show rich display based on TTY and user preference.

    Args:
        force_rich_display: User explicitly requested rich display

    Returns:
        True if rich display should be shown
    """
    return force_rich_display or tty.is_tty(sys.stdout)


def should_show_logs(force_show_logs: bool, show_rich_display: bool) -> bool:
    """Determine whether to show logs on stderr.

    Args:
        force_show_logs: User explicitly requested logs
        show_rich_display: Rich display is being shown

    Returns:
        True if logs should be shown
    """
    return force_show_logs or not show_rich_display or not tty.streams_have_same_destination(sys.stdout, sys.stderr)


@contextmanager
def buffered_stdout() -> Generator[TextIO | Any, None, None]:
    """
    Context manager that captures stdout during execution and replays it after exit.

    This is designed to work with Rich's Live display in screen mode. When Live uses
    screen=True, it switches to an alternate terminal screen, causing any stdout
    output (like print statements) during the Live display to be lost when returning
    to the main screen.

    This context manager:
    1. Redirects sys.stdout to a buffer during the 'with' block
    2. Yields the original stdout for use by Rich's Live display
    3. Replays all captured stdout content to the terminal after the 'with' block exits

    Usage:
        with buffered_stdout() as original_stdout:
            console = Console(file=original_stdout) # Use the real stdout for the Live display
            with Live(layout, console=console, screen=True) as live:
                print("This will be captured and shown after Live exits")
                # Live display code here
        # Captured print output appears here

    Returns:
        The original stdout stream for use by Rich's console
    """
    # String buffer to capture stdout while the live display is active
    buf = io.StringIO()

    old_out = sys.stdout
    try:
        sys.stdout = buf
        yield old_out
    finally:
        sys.stdout = old_out
        sys.stdout.write(buf.getvalue())
