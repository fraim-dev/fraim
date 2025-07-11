import os
import tempfile
from pathlib import Path
from typing import Any, Generator

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.file_chunks import chunk_input
from fraim.inputs.files import Files
from fraim.inputs.git import Git
from fraim.inputs.local import Local


class ProjectInput:
    config: Config
    files: Files
    chunk_size: int
    project_path: str
    repo_name: str

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        globs = kwargs.globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            temp_dir = tempfile.mkdtemp(prefix="fraim_scan_")
            self.project_path = os.path.join(temp_dir, "repo")
            self.config.logger.info(f"Cloning repository: {path_or_url} into path: {self.project_path}")
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            self.files = Git(self.config, url=path_or_url, tempdir=self.project_path, globs=globs, limit=limit)
        else:
            self.project_path = path_or_url
            self.repo_name = os.path.basename(os.path.abspath(path_or_url))
            self.files = Local(self.config, Path(path_or_url), globs=globs, limit=limit)

    def __iter__(self) -> Generator[CodeChunk, None, None]:
        for file in self.files:
            self.config.logger.info(f"Generating chunks for file: {file.path}")
            chunked = chunk_input(file, self.project_path, self.chunk_size)
            for chunk in chunked:
                yield chunk
