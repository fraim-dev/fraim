# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from __future__ import annotations

from pathlib import Path


class BasePathFS:
    """A file system wrapper that restricts access to a fixed root.

    All paths are:
      - joined to the root
      - fully resolved (symlinks + '..' segments)
      - verified to be descendants of the root

    If any check fails, a FileNotFoundError is raised.
    """

    def __init__(self, path: str | Path) -> None:
        base_path = Path(path).resolve()

        if not base_path.exists():
            raise FileNotFoundError(f"Base path does not exist: {path}")

        if not base_path.is_dir():
            raise NotADirectoryError(f"Base path is not a directory: {path}")

        self.root: Path = base_path

    def resolve(self, path: str | Path, *, must_exist: bool = False) -> Path:
        """Return an absolute, resolved path confined to root.

        If must_exist is True, ensure the path exists before returning.
        """
        # Join the user-supplied path to the root, then resolve symlinks & dot segments
        candidate = (self.root / (path or ".")).resolve()

        # Ensure the resolved path is inside the base path root
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise PermissionError(f"Path is outside of base path: {candidate}") from None

        if must_exist and not candidate.exists():
            raise FileNotFoundError(f"Path does not exist: {candidate}")
        return candidate

    def relative_to_root(self, p: str | Path) -> Path:
        """Return p as a path relative to the base path root (after resolution)."""
        rp = self.resolve(p)
        return rp.relative_to(self.root)
