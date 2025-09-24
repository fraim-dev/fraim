import os
from collections.abc import Iterator
from typing import Any

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.git import GitRemote
from fraim.inputs.git_diff import GitDiff
from fraim.inputs.input import Input
from fraim.inputs.local import Local


class ProjectInput:
    input: Input
    chunk_size: int
    project_path: str
    repo_name: str
    chunker: type["ProjectInputFileChunker"]

    # TODO: **kwargs?
    def __init__(self, kwargs: Any) -> None:
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.base = kwargs.base
        self.head = kwargs.head
        self.diff = kwargs.diff
        self.chunker = ProjectInputFileChunker

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            # TODO: git diff here?
            self.input = GitRemote(url=path_or_url, globs=globs, limit=limit, prefix="fraim_scan_")
            self.project_path = self.input.root_path()
        else:
            # Fully resolve the path to the project
            self.project_path = os.path.abspath(path_or_url)
            self.repo_name = os.path.basename(self.project_path)
            if self.diff:
                self.input = GitDiff(self.project_path, head=self.head, base=self.base, globs=globs, limit=limit)
            else:
                self.input = Local(self.project_path, globs=globs, limit=limit)

    def __iter__(self) -> Iterator[CodeChunk]:
        yield from self.input


class ProjectInputFileChunker:
    def __init__(self, file: BufferedFile, project_path: str, chunk_size: int) -> None:
        self.file = file
        self.project_path = project_path
        self.chunk_size = chunk_size

    def __iter__(self) -> Iterator[CodeChunk]:
        return chunk_input(self.file, self.chunk_size)
