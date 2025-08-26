# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for workflows that process code chunks with concurrent execution.
"""

import asyncio
from abc import abstractmethod
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, Any, Awaitable, Callable, List, Optional, Set, TypeVar

from fraim.config import Config
from fraim.core.contextuals import Contextual
from fraim.inputs.project import CHUNKING_METHODS, ProjectInput

from .workflow import WorkflowInput

# Type variable for generic result types
T = TypeVar("T")


@dataclass
class ChunkWorkflowInput(WorkflowInput):
    """Base input for chunk-based workflows."""

    config: Config
    head: Annotated[str, {"help": "Git head commit for diff input"}]
    base: Annotated[str, {"help": "Git base commit for diff input"}]
    location: Annotated[str, {"help": "Repository URL or path to scan"}]
    paths: Annotated[
        Optional[List[str]], {"help": "Optionally limit scanning to these paths (relative to `--location`)"}
    ] = None
    chunk_size: Annotated[Optional[int], {"help": "Number of characters per chunk"}] = 10_000
    chunk_overlap: Annotated[Optional[int], {"help": "Number of characters of overlap per chunk"}] = 1_000
    limit: Annotated[Optional[int], {"help": "Limit the number of files to scan"}] = None
    globs: Annotated[
        Optional[List[str]],
        {"help": "Globs to use for file scanning. If not provided, will use workflow-specific defaults."},
    ] = None
    exclude_globs: Annotated[
        Optional[List[str]],
        {"help": "Globs to use for file scanning. If not provided, will use workflow-specific defaults."},
    ] = None
    max_concurrent_chunks: Annotated[int, {"help": "Maximum number of chunks to process concurrently"}] = 5

    diff: Annotated[
        bool,
        {
            "help": (
                "Whether to use git diff input. If --head and --base are not specified, the working tree is scanned."
            )
        },
    ] = False
    chunking_method: Annotated[
        str, {
            "help": "Method to use for chunking code files",
            "choices": CHUNKING_METHODS.keys(),
        }
    ] = "fixed"



class ChunkProcessingMixin:
    """
    Mixin class providing utilities for chunk-based workflows.

    This class provides reusable utilities for:
    - Setting up ProjectInput from workflow input
    - Managing concurrent chunk processing with semaphores

    Workflows can use these utilities as needed while maintaining full control
    over their workflow() method and error handling.
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config
        # Note: In mixins, we often don't call super().__init__()
        # The concrete class will handle calling the base class __init__

    @property
    @abstractmethod
    def file_patterns(self) -> List[str]:
        """File patterns for this workflow (e.g., ['*.py', '*.js'])."""
        pass

    @property
    def exclude_file_patterns(self) -> List[str]:
        """File patterns for this workflow (e.g., ['*.py', '*.js'])."""
        return [
            '*.min.js',
            '*.min.css',
        ]

    def setup_project_input(self, input: ChunkWorkflowInput) -> ProjectInput:
        """
        Set up ProjectInput from workflow input.

        Args:
            input: The workflow input

        Returns:
            Configured ProjectInput instance
        """
        effective_globs = input.globs if input.globs is not None else self.file_patterns
        exclude_effective_globs = input.exclude_globs if input.exclude_globs is not None else self.exclude_file_patterns

        kwargs = SimpleNamespace(
            location=input.location,
            globs=effective_globs,
            exclude_globs=exclude_effective_globs,
            limit=input.limit,
            head=input.head,
            base=input.base,
            diff=input.diff,
            chunk_size=input.chunk_size,
            chunk_overlap=input.chunk_overlap,
            paths=input.paths,
            chunking_method=input.chunking_method,
        )
        return ProjectInput(config=self.config, kwargs=kwargs)

    async def process_chunks_concurrently(
        self,
        project: ProjectInput,
        chunk_processor: Callable[[Contextual[str]], Awaitable[List[T]]],
        max_concurrent_chunks: int = 5,
    ) -> List[T]:
        """
        Process chunks concurrently using the provided processor function.

        Args:
            project: ProjectInput instance to iterate over
            chunk_processor: Async function that processes a single chunk and returns a list of results
            max_concurrent_chunks: Maximum concurrent chunk processing

        Returns:
            Combined results from all chunks
        """
        results: List[T] = []

        # Create semaphore to limit concurrent chunk processing
        semaphore = asyncio.Semaphore(max_concurrent_chunks)

        async def process_chunk_with_semaphore(chunk: Contextual[str]) -> List[T]:
            """Process a chunk with semaphore to limit concurrency."""
            async with semaphore:
                return await chunk_processor(chunk)

        # Process chunks as they stream in from the ProjectInput iterator
        active_tasks: Set[asyncio.Task] = set()

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
