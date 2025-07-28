import os
from pathlib import Path
from typing import Any, Generator, Iterator, Type

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.file_chunks import chunk_input
from fraim.inputs.files import File, Files
from fraim.inputs.git import GitRemote
from fraim.inputs.local import Local


class ProjectInput:
    config: Config
    files: Files
    chunk_size: int
    project_path: str
    repo_name: str
    chunker: Type["ProjectInputFileChunker"]

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.chunker = ProjectInputFileChunker

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

    def __iter__(self) -> Generator[CodeChunk, None, None]:
        with self.files as files:
            for file in files:
                self.config.logger.info(f"Generating chunks for file: {file.path}")
                for chunk in chunk_input(file, self.project_path, self.chunk_size):
                    yield chunk


class ProjectInputFileChunker:
    def __init__(self, file: File, project_path: str, chunk_size: int) -> None:
        self.file = file
        self.project_path = project_path
        self.chunk_size = chunk_size

    def __iter__(self) -> Iterator[CodeChunk]:
        return iter(chunk_input(self.file, self.project_path, self.chunk_size))
