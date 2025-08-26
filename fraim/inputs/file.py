# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from pathlib import Path
from typing import ContextManager, Iterator, Protocol, runtime_checkable

from langchain_community.document_loaders.parsers.language.language_parser import LANGUAGE_EXTENSIONS

import mcp_server_tree_sitter

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path


class File:
    def __init__(self, path: str, body: str):
        self.path = path
        self.body = body

    @property
    def language(self) -> str | None:
        return LANGUAGE_EXTENSIONS.get(str(Path(self.path).suffix), None)


@runtime_checkable
class Files(Protocol, ContextManager):
    def __iter__(self) -> Iterator[File]: ...

    # The absolute file path that these files are relative to.
    def root_path(self) -> str: ...
