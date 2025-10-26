# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import logging
from typing import Iterator

from fraim.core.contextuals import Contextual
from fraim.core.contextuals.code import CodeChunks, CodeChunk
from fraim.inputs.chunkers.fixed import FixedTokenChunker
from fraim.inputs.chunkers.syntactic import SyntacticChunker

logger = logging.getLogger(__name__)

class PackingSyntacticChunker(SyntacticChunker):
    """
    A syntactic chunker that packs multiple whole files into chunks.

    This chunker implements a "bin packing" strategy. It iterates through the
    files, adding each one to a "pack" (a CodeChunks object). If adding the
    next file would cause the pack to exceed `chunk_size`, the current pack is
    yielded, and a new one is started.

    Rules:
    1. Files are split with SyntacticChunker before packing.
    2. If a single file is larger than `chunk_size`, it will be yielded by
       itself in its own chunk, violating the size limit to uphold rule #1.
    """

    def __iter__(self) -> Iterator[Contextual[str]]:
        yield from self.chunks()

    # Chunks is kept separate from iterator so we have a type annotation that returns the concrete class
    def chunks(self) -> Iterator[CodeChunks]:
        """
        Represents the packed chunks, each containing multiple files.

        This is the same as the __iter__ method, but with a more specific return type.
        """
        yield from packed_chunks(super().chunks(), self.chunk_size)



class PackingFixedTokenChunker(FixedTokenChunker):
    """
    A fixed token chunker that packs multiple whole files into chunks.

    This chunker implements a "bin packing" strategy. It iterates through the
    files, adding each one to a "pack" (a CodeChunks object). If adding the
    next file would cause the pack to exceed `chunk_size`, the current pack is
    yielded, and a new one is started.

    Rules:
    1. Files are split with FixedTokenChunker before packing.
    2. If a single file is larger than `chunk_size`, it will be yielded by
       itself in its own chunk, violating the size limit to uphold rule #1.
    """

    def __iter__(self) -> Iterator[Contextual[str]]:
        yield from self.chunks()

    # Chunks is kept separate from iterator so we have a type annotation that returns the concrete class
    def chunks(self) -> Iterator[CodeChunks]:
        """
        Represents the packed chunks, each containing multiple files.

        This is the same as the __iter__ method, but with a more specific return type.
        """
        yield from packed_chunks(super().chunks(), self.chunk_size)

def packed_chunks(chunks: Iterator[CodeChunk], chunk_size: int) -> Iterator[CodeChunks]:
    """
    Yields packed `CodeChunks`, each close to `chunk_size` without splitting files.
    """
    current_pack = CodeChunks()

    # Ensure smaller files are combined up to chunk_size, preserving order.
    for file_chunk in chunks:
        # Case 2: The current pack is empty. Add the first chunk.
        if not current_pack:
            current_pack.append(file_chunk)
            continue

        # Case 3: Try adding the new chunk to the existing pack.
        # We create a temporary CodeChunks object to accurately measure the
        # final string length, including all XML tags and newlines.
        size_if_added = len(CodeChunks(current_pack + [file_chunk]))

        if size_if_added > chunk_size:
            # It doesn't fit. Yield the current pack.
            logger.info(f"Generated chunk with files: {', '.join(current_pack.file_paths)}")
            yield current_pack
            # Start a new pack with the current file_chunk.
            current_pack = CodeChunks([file_chunk])
        else:
            # It fits! Add the chunk to the current pack.
            current_pack.append(file_chunk)

    # After the loop, if there's anything left in the final pack, yield it.
    if current_pack:
        logger.info(f"Generated chunk with files: {', '.join(current_pack.file_paths)}")
        yield current_pack
