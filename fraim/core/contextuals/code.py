# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from fraim.core.contextuals.contextual import Contextual


# TODO: Consider CodeDiff, other types of Contextuals
class CodeChunk(Contextual[str]):
    """Concrete implementation of Contextual for code snippets"""

    def __init__(self, file_path: str, content: str, line_number_start_inclusive: int, line_number_end_inclusive: int):
        self.content = content
        self.file_path = file_path
        self.line_number_start_inclusive = line_number_start_inclusive
        self.line_number_end_inclusive = line_number_end_inclusive

    @property
    def description(self) -> str:
        return f"Code chunk from {self.file_path}:{self.line_number_start_inclusive}-{self.line_number_end_inclusive}"

    @description.setter
    def description(self, _: str) -> None:
        raise AttributeError("description is read-only")

    # TODO: Change to repr
    def __str__(self) -> str:
        return f'<code_chunk file_path="{self.file_path}" line_number_start_inclusive="{self.line_number_start_inclusive}" line_number_end_inclusive="{self.line_number_end_inclusive}">\n{self.content}\n</code_chunk>'
