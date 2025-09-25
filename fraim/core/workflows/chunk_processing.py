# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for workflows that process code chunks with concurrent execution.
"""

import asyncio
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, Generic, TypeVar

from rich.layout import Layout
from rich.progress import Progress, TaskID

from fraim.core.contextuals import CodeChunk
from fraim.core.display import ProgressPanel, ResultsPanel
from fraim.core.history import EventRecord, History, HistoryRecord
from fraim.inputs.project import ProjectInput

# Type variable for generic result types
T = TypeVar("T")


@dataclass
class ChunkProcessingOptions:
    """Base input for chunk-based workflows."""

    location: Annotated[str, {"help": "Repository URL or path to scan"}] = "."
    chunk_size: Annotated[int | None, {"help": "Number of lines per chunk"}] = 500
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
    max_concurrent_chunks: Annotated[int, {"help": "Maximum number of chunks to process concurrently"}] = 5


class ChunkProcessor(Generic[T]):
    """
    Mixin class providing utilities for chunk-based workflows.

    This class provides reusable utilities for:
    - Setting up ProjectInput from workflow input
    - Managing concurrent chunk processing with semaphores
    - Rich display with progress tracking

    Workflows can use these utilities as needed while maintaining full control
    over their workflow() method and error handling.
    """

    def __init__(self, args: ChunkProcessingOptions) -> None:
        super().__init__(args)  # type: ignore

        # Progress tracking attributes
        self._total_chunks = 0
        self._processed_chunks = 0
        self._results: list[T] = []
        self._progress: Progress | None = None
        self._progress_task: TaskID | None = None

    @property
    @abstractmethod
    def file_patterns(self) -> list[str]:
        """File patterns for this workflow (e.g., ['*.py', '*.js'])."""

    def setup_project_input(self, args: ChunkProcessingOptions) -> ProjectInput:
        """
        Set up ProjectInput from workflow options.

        Args:
            args: Arguments to create the input.

        Returns:
            Configured ProjectInput instance
        """
        effective_globs = args.globs if args.globs is not None else self.file_patterns
        kwargs = SimpleNamespace(
            location=args.location,
            globs=effective_globs,
            limit=args.limit,
            chunk_size=args.chunk_size,
            head=args.head,
            base=args.base,
            diff=args.diff,
        )
        return ProjectInput(kwargs=kwargs)

    def rich_display(self) -> Layout:
        """
        Create a rich display layout showing:
        - Base class rich_display in the upper panel
        - Progress bar showing percentage of chunks processed
        - Panel showing number of results found so far
        """
        # Get the base class display - since workflows inherit from Workflow class,
        # this should always work for ChunkProcessor mixins
        base_display = super().rich_display()  # type: ignore[misc]

        # Create the main layout with three sections
        layout = Layout()
        layout.split_column(
            Layout(base_display, name="history", ratio=1),
            Layout(
                ProgressPanel(lambda: ("Analyzing chunks", self._processed_chunks, self._total_chunks)),
                name="progress",
                size=3,
            ),
            Layout(ResultsPanel(lambda: self._results), name="results", size=3),
        )

        return layout

    async def process_chunks_concurrently(
        self,
        history: History,
        project: ProjectInput,
        chunk_processor: Callable[[History, CodeChunk], Awaitable[list[T]]],
        max_concurrent_chunks: int = 5,
    ) -> list[T]:
        """
        Process chunks concurrently using the provided processor function.

        Args:
            history: History instance for tracking
            project: ProjectInput instance to iterate over
            chunk_processor: Async function that processes a single chunk and returns a list of results
            max_concurrent_chunks: Maximum concurrent chunk processing

        Returns:
            Combined results from all chunks
        """
        # Initialize progress tracking
        chunks_list = list(project)
        self._total_chunks = len(chunks_list)
        self._processed_chunks = 0
        self._results = []

        # Create semaphore to limit concurrent chunk processing
        semaphore = asyncio.Semaphore(max_concurrent_chunks)

        async def process_chunk_with_semaphore(history: History, chunk: CodeChunk) -> list[T]:
            """Process a chunk with semaphore to limit concurrency."""
            async with semaphore:
                chunk_results = await chunk_processor(history, chunk)

                history.append_record(EventRecord(description=f"Done. Found {len(chunk_results)} results."))
                self._results.extend(chunk_results)
                self._processed_chunks += 1

                return chunk_results

        # Process chunks concurrently
        active_tasks: set[asyncio.Task] = set()

        for chunk in chunks_list:
            # Create a subhistory for this task
            task_record = HistoryRecord(
                description=f"Analyzing {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}"
            )
            history.append_record(task_record)

            # Create task for this chunk and add to active tasks
            task = asyncio.create_task(process_chunk_with_semaphore(task_record.history, chunk))
            active_tasks.add(task)

            # If we've hit our concurrency limit, wait for some tasks to complete
            if len(active_tasks) >= max_concurrent_chunks:
                _done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

        # Wait for any remaining tasks to complete
        await asyncio.gather(*active_tasks)

        return self._results
