import os
from collections.abc import Iterator
from types import TracebackType
from typing import Any, Optional

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.git import GitRemote
from fraim.inputs.git_diff import GitDiff
from fraim.inputs.input import Input
from fraim.inputs.local import Local


class ProjectInput:
    config: Config
    input: Input
    chunk_size: int
    project_path: str
    repo_name: str
    chunker: type["ProjectInputFileChunker"]

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.base = kwargs.base
        self.head = kwargs.head
        self.diff = kwargs.diff
        self.chunker = ProjectInputFileChunker
        self._files_context_active = False

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            # TODO: git diff here?
            self.input = GitRemote(self.config, url=path_or_url, globs=globs, limit=limit, prefix="fraim_scan_")
            self.project_path = self.input.root_path()
        else:
            # Fully resolve the path to the project
            self.project_path = os.path.abspath(path_or_url)
            self.repo_name = os.path.basename(self.project_path)
            if self.diff:
                self.input = GitDiff(
                    self.config, self.project_path, head=self.head, base=self.base, globs=globs, limit=limit
                )
            else:
                self.input = Local(self.config, self.project_path, globs=globs, limit=limit)

    def __iter__(self) -> Iterator[CodeChunk]:
        yield from self.input

    def __enter__(self) -> "ProjectInput":
        """Enter the context manager by delegating to the underlying input."""
        self.input.__enter__()
        return self

    def __exit__(
        self,
        exc_type: "Optional[type[BaseException]]",
        exc_val: "Optional[BaseException]",
        exc_tb: "Optional[TracebackType]",
    ) -> None:
        """Exit the context manager by delegating to the underlying input."""
        self.input.__exit__(exc_type, exc_val, exc_tb)


class ProjectInputFileChunker:
    def __init__(self, file: BufferedFile, project_path: str, chunk_size: int) -> None:
        self.file = file
        self.project_path = project_path
        self.chunk_size = chunk_size

    def __iter__(self) -> Iterator[CodeChunk]:
        return chunk_input(self.file, self.chunk_size)
