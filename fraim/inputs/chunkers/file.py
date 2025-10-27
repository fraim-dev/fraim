# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Any, Iterator

from litellm import get_max_tokens

from fraim.core.contextuals import Contextual
from fraim.inputs.chunkers.fixed import FixedTokenChunker


class FileChunker(FixedTokenChunker):
    """
    A chunker that yields each file as a single chunk if it fits in the LLMs context window.

    If it does not fit, it will be split with FixedTokenChunker.
    """

    def __init__(self, model: str, chunk_fraction: float = 0.7, **kwargs: Any) -> None:
        max_tokens = get_max_tokens(model)
        if not max_tokens:
            max_tokens = 100_000
        chunk_size = max_tokens * chunk_fraction

        kwargs.pop("chunk_size", None)  # Use are own chunk size here
        kwargs.pop("chunk_overlap", None)  # Use are own chunk size here
        super().__init__(chunk_size=int(chunk_size), chunk_overlap=0, **kwargs)

    def __iter__(self) -> Iterator[Contextual[str]]:
        """Yield each file as a single chunk."""

        yield from self.chunks()
