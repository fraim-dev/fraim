# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path
from typing import ContextManager, Iterator, Protocol, runtime_checkable


class File:
    def __init__(self, path: Path, body: str):
        self.path = path
        self.body = body


@runtime_checkable
class Files(Protocol, ContextManager):
    def __iter__(self) -> Iterator[File]: ...

    # The absolute file path that these files are relative to.
    def root_path(self) -> str: ...
