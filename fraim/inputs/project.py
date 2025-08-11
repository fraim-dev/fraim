import os
from pathlib import Path
from typing import Any, Iterator, Type, Literal

from fraim.config.config import Config
<< << << < HEAD
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.chunkers import ProjectInputChunker, FileChunker, ProjectChunker
from fraim.inputs.chunkers.base import Chunker
== == == =
from fraim.core.contextuals.code import CodeChunk, CodeChunks
from fraim.inputs.chunkers import FileChunker, ProjectChunker
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.chunkers.fixed import FixedChunker
from fraim.inputs.files import Files
>> >> >> > c036e37(Refactor: Improve
chunking
method
flexibility and prepare
for benchmarking)
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

    chunker: FixedChunker | FileChunker | ProjectChunker
    chunking_method: Literal["project", "file", "module", "fixed", "ast"] = "fixed"
    no_op: bool = False

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.base = kwargs.base
        self.head = kwargs.head
        self.diff = kwargs.diff
        self.chunking_method = kwargs.chunking_method
        self.no_op = kwargs.no_op

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
        chunker_class: type[Chunker]
        if self.chunking_method == "fixed":
            chunker_class = FixedChunker
        elif self.chunking_method == "file":
            chunker_class = FileChunker
        elif self.chunking_method == "project":
            chunker_class: Type[FixedChunker] = FixedChunker
        else:
            raise ValueError(f"Unsupported chunking method: {self.chunking_method}")

        self.chunker = chunker_class(
            files=self.files,
            project_path=self.project_path,
            chunk_size=self.chunk_size,
            config=self.config,
        )
