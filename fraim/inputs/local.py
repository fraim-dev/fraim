# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import itertools
from pathlib import Path
from types import TracebackType
from typing import Iterator, List, Optional, Type

from typing_extensions import Self

from fraim.config.config import Config
from fraim.inputs.files import File, Files


class Local(Files):
    def __init__(self, config: Config, path: Path, globs: Optional[List[str]] = None, limit: Optional[int] = None):
        self.config = config
        self.path = path
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
        self.limit = limit

    def root_path(self) -> str:
        return self.path.name

    def __iter__(self) -> Iterator[File]:
        self.config.logger.info(f"Scanning local files: {self.path}, with globs: {self.globs}")
        gen = self._files()
        if self.limit is not None:
            return itertools.islice(gen, self.limit)
        return gen

    def _files(self) -> Iterator[File]:
        seen = set()
        for glob_pattern in self.globs:
            for path in self.path.rglob(glob_pattern):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    self.config.logger.info(f"Reading file: {path}")
                    try:
                        yield File(
                            path, path.read_text(encoding="utf-8")
                        )  # buffer the files one at a time. avoid reading files that are too large?
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
