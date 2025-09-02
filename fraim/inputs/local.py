# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os.path
from pathlib import Path
from types import TracebackType
from typing import Iterator, List, Optional, Type

from typing_extensions import Self

from fraim.config.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.inputs.input import Input


class Local(Input):
    def __init__(
        self,
        config: Config,
        root_path: str,
        paths: Optional[list[str]] = None,
        globs: Optional[List[str]] = None,
        limit: Optional[int] = None,
        exclude_globs: Optional[List[str]] = None,
    ):
        self.config = config
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

    def root_path(self) -> str:
        return str(self._root_path)

    def __iter__(self) -> Iterator[CodeChunk]:
        self.config.logger.info(f"Scanning local files: {self.root_path}, with globs: {self.globs}")

        seen = set()
        for subpath in self.paths:
            subpath = Path(subpath)
            self.config.logger.info(
                f"Scanning local files: {subpath}, with globs: {self.globs}, exclude globs: {self.exclude_globs}"
            )
            for glob_pattern in self.globs:
                paths: Iterator[Path]
                if subpath.is_file():
                    paths = iter([subpath])
                else:
                    paths = subpath.rglob(glob_pattern)

                for path in paths:
                    if any(path.match(exclude) for exclude in self.exclude_globs):
                        self.config.logger.debug(f"Skipping excluded file: {path}")
                    else:
                        # Skip file if not a file
                        if not path.is_file():
                            continue

                        if any(path.match(exclude) for exclude in self.exclude_globs):
                            self.config.logger.debug(f"Skipping excluded file: {path}")
                            continue

                        # Skip file if already seen
                        if path in seen:
                            continue
                        try:
                            self.config.logger.info(f"Reading file: {path}")
                            # TODO: Avoid reading files that are too large?
                            content = path.read_text(encoding="utf-8")
                            yield CodeChunk(
                                file_path=os.path.relpath(path, self._root_path),
                                content=content,
                                line_number_start_inclusive=1,
                                line_number_end_inclusive=len(content),
                            )

                            # Add file to set of seen files, exit early if maximum reached.
                            seen.add(path)
                            if self.limit is not None and len(seen) == self.limit:
                                return

                        except Exception as e:
                            if isinstance(e, UnicodeDecodeError):
                                self.config.logger.warning(f"Skipping file with encoding issues: {path}")
                                continue
                            self.config.logger.error(f"Error reading file: {path} - {e}")
                            raise e

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        pass
