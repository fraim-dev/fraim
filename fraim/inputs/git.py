# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

from fraim.core.contextuals import CodeChunk
from fraim.inputs.input import Input
from fraim.inputs.local import Local

logger = logging.getLogger(__name__)


class GitRemote(Input):
    def __init__(
        self,
        url: str,
        globs: list[str] | None = None,
        limit: int | None = None,
        prefix: str | None = None,
    ):
        self.url = url
        self.globs = globs
        self.limit = limit
        self.tempdir = TemporaryDirectory(prefix=prefix)
        self.path = self.tempdir.name

    def root_path(self) -> str:
        return Path(self.path).absolute().name

    def __enter__(self) -> "GitRemote":
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None
    ) -> None:
        self.tempdir.cleanup()

    def __iter__(self) -> Iterator[CodeChunk]:
        logger.debug("Starting git repository input iterator")

        # Clone remote repository to a local directory, delegate to file iterator.
        self._clone_to_path()
        for chunk in Local(self.path, self.globs, self.limit):
            yield chunk

    def _clone_to_path(self) -> None:
        if not _is_directory_empty(self.path):
            logger.debug(f"Target directory {self.path} not empty, skipping git clone")
            return

        logger.info(f"Cloning repository: {self.url}")
        result = subprocess.run(
            args=["git", "clone", "--depth", "1", self.url, self.path], check=False, capture_output=True, text=True
        )

        if result.returncode != 0:
            logger.error(f"Git clone failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        logger.info("Repository cloned: {tempdir}")


def _is_directory_empty(path: str) -> bool:
    return os.path.isdir(path) and not os.listdir(path)
