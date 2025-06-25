# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os
from typing import List

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.files import File


# TODO: generator
def chunk_input(file: File, project_path: str, chunk_size: int) -> List[CodeChunk]:
    """Split file content into chunks with line numbers."""
    lines = file.body.split("\n")
    chunks = []
    file_path = os.path.relpath(str(file.path), project_path)

    # If file is small enough, just process it as a single chunk
    if len(lines) <= chunk_size:
        return [CodeChunk(file.body, file_path, 1, len(lines) - 1)]

    # Create chunks at logical boundaries
    for i in range(0, len(lines), chunk_size):
        chunk_start = i

        # If we're not at the beginning, try to find a better starting point
        if i > 0:
            # Look back up to 20 lines to find a better boundary
            for j in range(max(0, i - 20), i):
                line = lines[j].strip()
                # Good boundary markers: empty lines, beginning of blocks, end of blocks
                if not line or line == "{" or line.endswith("{") or line == "}" or line.endswith("}"):
                    chunk_start = j
                    break

        chunk_end = min(i + chunk_size, len(lines))

        # If we're not at the end, try to find a better ending point
        if chunk_end < len(lines):
            # Look ahead up to 20 lines to find a better boundary
            for j in range(chunk_end, min(chunk_end + 20, len(lines))):
                line = lines[j].strip()
                if not line or line == "{" or line.endswith("{") or line == "}" or line.endswith("}"):
                    chunk_end = j + 1  # Include the boundary line
                    break

            # Special check for lines ending with backslash (continuation lines)
            if 0 < chunk_end < len(lines):
                if lines[chunk_end - 1].strip().endswith("\\"):
                    # Find the end of this continued line
                    continuation_end = chunk_end
                    while continuation_end < len(lines) and lines[continuation_end - 1].strip().endswith("\\"):
                        continuation_end += 1
                        if continuation_end >= len(lines):
                            break
                    # Include at least 3 more lines after the continuation
                    chunk_end = min(len(lines), continuation_end + 3)

        chunk_content = "\n".join(lines[chunk_start:chunk_end])
        numbered_content = prepend_line_numbers_to_snippet(chunk_content)
        chunks.append(CodeChunk(numbered_content, file_path, chunk_start, chunk_end))

    return chunks


def prepend_line_numbers_to_snippet(snippet: str) -> str:
    # Add line numbers to the code snippet
    numbered_lines = []
    for i, line in enumerate(snippet.split("\n"), 1):
        numbered_lines.append(f"{i:3d}: {line}")

    joined_lines = "\n".join(numbered_lines)
    return joined_lines
