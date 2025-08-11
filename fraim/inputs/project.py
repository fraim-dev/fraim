import os
from pathlib import Path
from typing import Any, Iterator, Type, Literal

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk, CodeChunks
from fraim.inputs.chunkers import FileChunker, ProjectChunker
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.chunkers.fixed import FixedChunker
from fraim.inputs.files import Files
from fraim.inputs.git import GitRemote
from fraim.inputs.local import Local


class ProjectInput:
    config: Config
    files: Files
    chunk_size: int
    project_path: str
    repo_name: str
    chunker: FixedChunker|FileChunker|ProjectChunker
    chunking_method: Literal["project", "file", "module", "fixed", "ast"] = "fixed"
    no_op: bool = False

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.chunking_method = kwargs.chunking_method
        self.no_op = kwargs.no_op

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            self.files = GitRemote(self.config, url=path_or_url, globs=globs, limit=limit, prefix="fraim_scan_")
            self.project_path = self.files.root_path()
        else:
            self.project_path = path_or_url
            self.repo_name = os.path.basename(os.path.abspath(path_or_url))
            self.files = Local(self.config, Path(path_or_url), globs=globs, limit=limit)

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

    def __iter__(self) -> Iterator[CodeChunks|CodeChunk]:
        return iter(self.chunker)

