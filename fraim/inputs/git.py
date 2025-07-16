# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Iterator, List, Optional, Type

from typing_extensions import Self

from fraim.config.config import Config
from fraim.inputs.files import File, Files
from fraim.inputs.local import Local


def _remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree that attempts to remove read-only files.
    """
    # Check if the error is a PermissionError
    if issubclass(excinfo[1].__class__, PermissionError):
        # Change the file permissions to writable
        os.chmod(path, stat.S_IWRITE)
        # Retry the function that failed
        func(path)


class Git(Files):
    def __init__(
        self,
        config: Config,
        url: str,
        tempdir: Optional[str] = None,
        globs: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        self.config = config
        self.url = url
        self.tempdir = tempdir
        self.globs = globs
        self.limit = limit

    def __iter__(self) -> Iterator[File]:
        if self.tempdir:
            files_input = Local(self.config, Path(self.tempdir), self.globs, self.limit)
            return iter(files_input)
        return iter([])

    def __enter__(self) -> Self:
        self.tempdir = self.tempdir if self.tempdir else tempfile.mkdtemp()
        result = subprocess.run(["git", "clone", self.url, self.tempdir], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Git clone failed with error:\n{result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        if self.tempdir:
            shutil.rmtree(self.tempdir, onerror=_remove_readonly)
            self.tempdir = None
