# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for workflows that process code chunks with concurrent execution.
"""

import asyncio
import logging
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, TypeVar

from fraim.core.contextuals import Contextual
from fraim.core.workflows.llm_processing import LLMOptions
from fraim.inputs.project import CHUNKING_METHODS, ProjectInput

# Type variable for generic result types
T = TypeVar("T")


@dataclass
class ChunkProcessingOptions(LLMOptions):
    """Base input for chunk-based workflows."""

    location: Annotated[str, {"help": "Repository URL or path to scan"}] = "."
    limit: Annotated[int | None, {"help": "Limit the number of files to scan"}] = None

    diff: Annotated[bool, {"help": "Whether to use git diff input"}] = False
    head: Annotated[str | None, {"help": "Git head commit for diff input, uses HEAD if not provided"}] = None
    base: Annotated[str | None, {"help": "Git base commit for diff input, assumes the empty tree if not provided"}] = (
        None
    )
    globs: Annotated[
        list[str] | None,
        {"help": "Globs to use for file scanning. If not provided, will use workflow-specific defaults."},
    ] = None
    exclude_globs: Annotated[
        list[str] | None,
        {"help": "Globs to use for file scanning. If not provided, will use workflow-specific defaults."},
    ] = None
    chunking_method: Annotated[
        str,
        {
            "help": (
                "Method to use for chunking code files. Only the original chunking method is supported currently. "
            ),
            "choices": CHUNKING_METHODS.keys(),
        },
    ] = "original"
    chunk_size: Annotated[
        int | None,
        {
            "help": (
                "Number of characters per chunk. Does not apply when the original, file, or project chunking methods are used."
            )
        },
    ] = 500
    paths: Annotated[
        list[str] | None, {"help": "Optionally limit scanning to these paths (relative to `--location`)"}
    ] = None
    chunk_overlap: Annotated[
        int | None,
        {
            "help": (
                "Number of characters of overlap per chunk. Does not apply when the original, file, or project chunking "
                "methods are used."
            )
        },
    ] = None
    max_concurrent_chunks: Annotated[int, {"help": "Maximum number of chunks to process concurrently"}] = 5


class ChunkProcessor:
    """
    Mixin class providing utilities for chunk-based workflows.

    This class provides reusable utilities for:
    - Setting up ProjectInput from workflow input
    - Managing concurrent chunk processing with semaphores

    Workflows can use these utilities as needed while maintaining full control
    over their workflow() method and error handling.
    """

    @property
    @abstractmethod
    def file_patterns(self) -> list[str]:
        """File patterns for this workflow (e.g., ['*.py', '*.js'])."""
        pass

    @property
    def exclude_file_patterns(self) -> list[str]:
        """File patterns for this workflow (e.g., ['*.py', '*.js'])."""
        return [
            "*.min.js",
            "*.min.css",
        ]

    def setup_project_input(self, logger: logging.Logger, args: ChunkProcessingOptions) -> ProjectInput:
        """
        Set up ProjectInput from workflow options.

        Args:
            args: Arguments to create the input.

        Returns:
            Configured ProjectInput instance
        """
        effective_globs = args.globs if args.globs is not None else self.file_patterns
        exclude_effective_globs = args.exclude_globs if args.exclude_globs is not None else self.exclude_file_patterns
        kwargs = SimpleNamespace(
            location=args.location,
            paths=args.paths,
            globs=effective_globs,
            exclude_globs=exclude_effective_globs,
            limit=args.limit,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            chunking_method=args.chunking_method,
            head=args.head,
            base=args.base,
            diff=args.diff,
            model=args.model,
        )
        return ProjectInput(logger, kwargs=kwargs)

    @staticmethod
    async def process_chunks_concurrently(
        project: ProjectInput,
        chunk_processor: Callable[[Contextual[str]], Awaitable[list[T]]],
        max_concurrent_chunks: int = 5,
    ) -> list[T]:
        """
        Process chunks concurrently using the provided processor function.

        Args:
            project: ProjectInput instance to iterate over
            chunk_processor: Async function that processes a single chunk and returns a list of results
            max_concurrent_chunks: Maximum concurrent chunk processing

        Returns:
            Combined results from all chunks
        """
        results: list[T] = []

        # Create semaphore to limit concurrent chunk processing
        semaphore = asyncio.Semaphore(max_concurrent_chunks)

        async def process_chunk_with_semaphore(chunk: Contextual[str]) -> list[T]:
            """Process a chunk with semaphore to limit concurrency."""
            async with semaphore:
                return await chunk_processor(chunk)

        # Process chunks as they stream in from the ProjectInput iterator
        active_tasks: set[asyncio.Task] = set()

        for chunk in project:
            # Create task for this chunk and add to active tasks
            task = asyncio.create_task(process_chunk_with_semaphore(chunk))
            active_tasks.add(task)

            # If we've hit our concurrency limit, wait for some tasks to complete
            if len(active_tasks) >= max_concurrent_chunks:
                done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                for completed_task in done:
                    chunk_results = await completed_task
                    results.extend(chunk_results)

        # Wait for any remaining tasks to complete
        if active_tasks:
            for future in asyncio.as_completed(active_tasks):
                chunk_results = await future
                results.extend(chunk_results)

        return results
