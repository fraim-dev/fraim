# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Iterator, List

from fraim.core.contextuals import Contextual
from fraim.core.contextuals.code import CodeChunk, CodeChunks
from fraim.inputs.chunkers.syntactic import SyntacticChunker


class PackingFixedChunker(SyntacticChunker):
    """
    A chunker that packs multiple whole files into chunks.

    This chunker implements a "bin packing" strategy. It iterates through the
    files, adding each one to a "pack" (a CodeChunks object). If adding the
    next file would cause the pack to exceed `chunk_size`, the current pack is
    yielded, and a new one is started.

    Rules:
    1. Files are split with FixedChunker before packing.
    2. If a single file is larger than `chunk_size`, it will be yielded by
       itself in its own chunk, violating the size limit to uphold rule #1.
    """

    def __iter__(self) -> Iterator[Contextual[str]]:
        yield from self.packed_chunks()


    def packed_chunks(self) -> Iterator[CodeChunks]:
        """
        Yields packed `CodeChunks`, each close to `chunk_size` without splitting files.
        """
        current_pack = CodeChunks()

        # Ensure smaller files are combined up to chunk_size, preserving order.
        for file_chunk in super().chunks():
            # Case 2: The current pack is empty. Add the first chunk.
            if not current_pack:
                current_pack.append(file_chunk)
                continue

            # Case 3: Try adding the new chunk to the existing pack.
            # We create a temporary CodeChunks object to accurately measure the
            # final string length, including all XML tags and newlines.
            size_if_added = len(str(CodeChunks(current_pack + [file_chunk])))

            if size_if_added > self.chunk_size:
                # It doesn't fit. Yield the current pack.
                self.logger.info(f"Generated chunk with files: {', '.join(current_pack.file_paths)}")
                yield current_pack
                # Start a new pack with the current file_chunk.
                current_pack = CodeChunks([file_chunk])
            else:
                # It fits! Add the chunk to the current pack.
                current_pack.append(file_chunk)

        # After the loop, if there's anything left in the final pack, yield it.
        if current_pack:
            self.logger.info(f"Generated chunk with files: {', '.join(current_pack.file_paths)}")
            yield current_pack
