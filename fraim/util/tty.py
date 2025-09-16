# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""TTY utilities."""

import io
import os
import sys
from typing import IO, Any


def is_tty(s: IO[Any] = sys.stdout) -> bool:
    """
    Returns True if the stream is a TTY.
    """
    return s.isatty()


def streams_have_same_destination(a: IO[Any], b: IO[Any]) -> bool:
    """
    Check if two I/O streams write to the same underlying destination.

    This function determines whether two streams (like stdout and stderr) are
    redirected to the same file or device by comparing their file descriptors'
    device and inode numbers.

    Args:
        a: First I/O stream to compare
        b: Second I/O stream to compare

    Returns:
        True if both streams write to the same destination (same device and inode),
        False if they write to different destinations or if file descriptors
        cannot be obtained.

    Examples:
        >>> import sys
        >>> # Check if stdout and stderr go to the same place
        >>> streams_have_same_destination(sys.stdout, sys.stderr)
        True  # When both are terminal

        >>> # When stderr is redirected to a file
        >>> streams_have_same_destination(sys.stdout, sys.stderr)
        False  # Different destinations
    """
    try:
        a_fd, b_fd = a.fileno(), b.fileno()
    except (AttributeError, io.UnsupportedOperation):
        # Can't obtain file descriptors. Assume different.
        return False

    try:
        sa, sb = os.fstat(a_fd), os.fstat(b_fd)
    except OSError:
        return False

    return (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino)
