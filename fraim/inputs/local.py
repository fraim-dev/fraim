# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import functools
import logging
import os.path
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

import pathspec

from fraim.core.contextuals import CodeChunk
from fraim.inputs.input import Input

logger = logging.getLogger(__name__)


class Local(Input):
    def __init__(
            self,
            root_path: str,
            paths: list[str] | None = None,
            globs: list[str] | None = None,
            limit: int | None = None,
            exclude_globs: list[str] | None = None,
    ):
        self._root_path = Path(root_path)

        if paths:
            self.paths = [Path(self._root_path) / p for p in paths]
        else:
            self.paths = [self._root_path]

        # TODO: remove hardcoded globs
        self.globs = (
            globs
            if globs
            else [
                "*.py",
                "*.c",
                "*.cpp",
                "*.h",
                "*.go",
                "*.ts",
                "*.js",
                "*.java",
                "*.rb",
                "*.php",
                "*.swift",
                "*.rs",
                "*.kt",
                "*.scala",
                "*.tsx",
                "*.jsx",
            ]
        )
        self.exclude_globs = exclude_globs if exclude_globs else ["*.min.js", "*.min.css"]
        self.limit = limit

    @property
    def root_path(self) -> str:
        return str(self._root_path)

    @functools.cached_property
    def gitignore_spec(self) -> None | pathspec.PathSpec:
        """Load .gitignore patterns if present"""
        gitignore_file = Path(self.root_path) / ".gitignore"
        if gitignore_file.exists():
            with gitignore_file.open() as f:
                return pathspec.PathSpec.from_lines("gitwildmatch", f)
        return None

    def __iter__(self) -> Iterator[CodeChunk]:
        logger.info(f"Scanning local files: {self.root_path}, with globs: {self.globs}")

        self._seen = set()
        for subpath in self.paths:
            subpath = Path(subpath)
            logger.info(
                f"Scanning local files: {subpath}, with globs: {self.globs}, exclude globs: {self.exclude_globs}"
            )
            for glob_pattern in self.globs:
                for path in rglob(subpath, glob_pattern):
                    if self.limit is not None and len(self._seen) == self.limit:
                        return

                    if self.should_scan_file(path):
                        try:
                            logger.info(f"Reading file: {path}")
                            # TODO: Avoid reading files that are too large?
                            content = path.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            logger.warning(f"Skipping file with encoding issues: {path}")
                            continue
                        except Exception as e:
                            logger.error(f"Error reading file: {path} - {e}")
                            raise

                        self._seen.add(path)
                        line_count = content.count("\n") + 1 if content else 0
                        yield CodeChunk(
                            file_path=os.path.relpath(path, self._root_path),
                            content=content,
                            line_number_start_inclusive=1,
                            line_number_end_inclusive=line_count,
                        )

    def should_scan_file(self, path: Path) -> bool:
        # Skip file if not a file
        if not path.is_file():
            logger.debug(f"Skipping, not a file: {path}")
            return False

        if any(path.match(exclude) for exclude in self.exclude_globs):
            logger.debug(f"Skipping, matches excluded globs {self.exclude_globs}: {path}")
            return False

        # Skip file if already seen
        if path in self._seen:
            return False

        # Skip git-ignored file
        # TODO: skipping here still requires the `rglob` step to iterate every file. Replace with a
        #       custom walk function that can skip entire branches.
        if self.gitignore_spec and self.gitignore_spec.match_file(path.relative_to(self.root_path).as_posix()):
            logger.debug(f"Skipping, ignored by .gitignore: {path}")
            return False
        return True

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass

def rglob(path: Path, glob_pattern: str):
    """Returns all matching paths or the path itself."""
    paths: Iterator[Path]
    if path.is_file():
        return iter([path])
    else:
        return path.rglob(glob_pattern)
