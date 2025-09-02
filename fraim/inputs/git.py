# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, List, Optional, Type

from fraim.config.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.inputs.input import Input
from fraim.inputs.local import Local


class GitRemote(Input):
    def __init__(
        self,
        config: Config,
        url: str,
        globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
        limit: int | None = None,
        prefix: str | None = None,
        paths: List[str] | None = None,
    ):
        self.config = config
        self.url = url
        self.globs = globs
        self.exclude_globs = exclude_globs
        self.limit = limit
        self.tempdir = TemporaryDirectory(prefix=prefix)
        self.path = self.tempdir.name
        self.paths = paths

    def root_path(self) -> str:
        return Path(self.path).absolute().name

    def __enter__(self) -> "GitRemote":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None
    ) -> None:
        self.tempdir.cleanup()

    def __iter__(self) -> Iterator[CodeChunk]:
        self.config.logger.debug("Starting git repository input iterator")

        # Clone remote repository to a local directory, delegate to file iterator.
        self._clone_to_path()
        for file in Local(self.config, self.path, self.paths, self.globs, self.limit, self.exclude_globs):
            yield CodeChunk(
                file_path=file.file_path,
                content=file.content,
                line_number_start_inclusive=1,
                line_number_end_inclusive=len(file.content),
            )

    def _clone_to_path(self) -> None:
        if not _is_directory_empty(self.path):
            self.config.logger.debug(f"Target directory {self.path} not empty, skipping git clone")
            return

        self.config.logger.info(f"Cloning repository: {self.url}")
        result = subprocess.run(
            args=["git", "clone", "--depth", "1", self.url, self.path], check=False, capture_output=True, text=True
        )

        if result.returncode != 0:
            self.config.logger.error(f"Git clone failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        self.config.logger.info("Repository cloned: {tempdir}")


def _is_directory_empty(path: str) -> bool:
    return os.path.isdir(path) and not os.listdir(path)
