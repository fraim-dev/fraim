# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import ContextManager, Dict, Iterator, Protocol, runtime_checkable

from fraim.core.contextuals import CodeChunk

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from pathlib import Path


class BufferedFile(CodeChunk):
    def __init__(self, path: str, body: str):
        super().__init__(file_path=path, content=body, line_number_start_inclusive=1, line_number_end_inclusive=len(body))
        self.path = path
        self.body = body

    def __str__(self) -> str:
        return f'<file path="{self.file_path}">\n{self.content}\n</file>'