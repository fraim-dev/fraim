# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Iterator

from fraim.core.contextuals.code import CodeChunks
from fraim.inputs.chunkers.file import FileChunker


class ProjectChunker(FileChunker):
    def __iter__(self) -> Iterator[CodeChunks]:
        """Yield the whole project as a single chunk."""

        all_files = list(super().__iter__())
        yield CodeChunks(
            description=f"All code in the project",
            *all_files,
        )
