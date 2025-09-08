# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Any, Iterator

from litellm import get_max_tokens

from fraim.inputs.chunkers.packed_fixed import PackingFixedChunker


class MaxContextChunker(PackingFixedChunker):
    """
    MaxContextChunker for using the full context window of an LLM.

    The MaxContextChunker yields chunks consisting of as many full files that can be returned before
    exceeding a specified percentage of the model's maximum token limit given.


    PackingFixedChunker can be used here because it does not split files when chunk_size is larger than the file size.

    Args:
        model (str): The name of the LLM model to determine max tokens.
        chunk_fraction (int, optional): The fraction of the model's max tokens to use.
        **kwargs: Additional arguments passed to the FileChunker.
    ."""

    def __init__(self, model: str, chunk_fraction: float = 0.7, **kwargs: Any) -> None:
        # Chunk size is determined by the model's max tokens and chunk_fraction.
        max_tokens = get_max_tokens(model)
        if not max_tokens:
            max_tokens = 100_000
        chunk_size = max_tokens * chunk_fraction

        kwargs.pop('chunk_size', None)  # Use are own chunk size here
        kwargs.pop('chunk_overlap', None)  # Use are own chunk size here

        super().__init__(chunk_size=int(chunk_size), chunk_overlap=0, **kwargs)
