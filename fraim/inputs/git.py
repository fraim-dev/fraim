# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, List, Optional

from fraim.config.config import Config
from fraim.inputs.files import File, Files
from fraim.inputs.local import Local

class GitRemote(Files):
    def __init__(
        self,
        config: Config,
        url: str,
        globs: Optional[List[str]] = None,
        limit: Optional[int] = None,
        prefix: Optional[str] = None,
    ):
        self.config = config
        self.url = url
        self.globs = globs
        self.limit = limit
        self.tempdir = TemporaryDirectory(prefix=prefix)

    def root_path(self) -> str:
        return self.tempdir.name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tempdir.cleanup()

    def __iter__(self) -> Iterator[File]:
        self.config.logger.debug("Starting git repository input iterator")

        # Clone remote repository to a local directory, delegate to file iterator.
        self._clone_to_path()
        for file in Local(self.config, self.path, self.globs, self.limit):
            yield file

    def _clone_to_path(self) -> None:
        if not _is_directory_empty(self.path.name):
            self.config.logger.debug("Target directory not empty, skipping git clone")
            return

        self.config.logger.info(f"Cloning repository: {self.path.name}")
        result = subprocess.run(
            args=["git", "clone", "--depth", "1", self.url, self.path.name],
            check=False,
            capture_output=True,
            text=True)

        if result.returncode != 0:
            self.config.logger.error(f"Git clone failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        else:
            self.config.logger.info("Repository cloned: {tempdir}")


def _is_directory_empty(path):
    return os.path.isdir(path) and not os.listdir(path)
