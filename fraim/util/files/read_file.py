# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from __future__ import annotations

from pathlib import Path

from .basepath import BasePathFS


def read_file(fs: BasePathFS, target_path: str | Path, *, offset: int | None = None, limit: int | None = None) -> str:
    """Read a file with optional line-based offset and limit.

    Args:
        fs: BasePathFS instance to use for path resolution
        target_path: Path to the file to read
        offset: Starting line number (1-based). If None, start from beginning
        limit: Maximum number of lines to read. If None, read all lines

    Returns:
        File content as string, optionally limited by offset and limit
    """

    p = fs.resolve(target_path, must_exist=True)
    if not p.is_file():
        raise IsADirectoryError(f"Not a regular file: {p}")

    with p.open("r", encoding="utf-8", errors="replace") as fh:
        # Read entire file
        if offset is None and limit is None:
            return fh.read()

        # Read line by line for offset/limit support
        lines = []
        for line_num, line in enumerate(fh, start=1):
            # Skip lines before offset
            if offset is not None and line_num < offset:
                continue

            # Keep line after offset
            lines.append(line)

            # Stop at the limit
            if limit is not None and len(lines) >= limit:
                break

        return "".join(lines)
