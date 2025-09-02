import os
from collections.abc import Iterator
from typing import Any, Literal

from fraim.config.config import Config
from fraim.core.contextuals import CodeChunk, Contextual
from fraim.inputs.chunkers import FileChunker, MaxContextChunker
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.chunkers.fixed import FixedTokenChunker
from fraim.inputs.chunkers.original import OriginalChunker
from fraim.inputs.chunkers.packed_fixed import PackingFixedChunker
from fraim.inputs.chunkers.syntactic import SyntacticChunker
from fraim.inputs.git import GitRemote
from fraim.inputs.git_diff import GitDiff
from fraim.inputs.input import Input
from fraim.inputs.local import Local

CHUNKING_METHODS = {
    "syntactic": SyntacticChunker,
    "fixed_token": FixedTokenChunker,
    "packed": PackingFixedChunker,
    "file": FileChunker,
    "project": MaxContextChunker,
    "original": OriginalChunker,
}


class ProjectInput:
    config: Config
    input: Input
    chunk_size: int
    chunk_overlap: int = 0
    project_path: str
    repo_name: str
    chunker: Chunker
    chunking_method: Literal["syntactic", "fixed", "fixed_token", "packed", "file", "project", "original"] = "original"

    def __init__(self, config: Config, kwargs: Any) -> None:
        self.config = config
        path_or_url = kwargs.location or None
        paths = kwargs.paths
        globs = kwargs.globs
        exclude_globs = kwargs.exclude_globs
        limit = kwargs.limit
        self.chunk_size = kwargs.chunk_size
        self.chunk_overlap = kwargs.chunk_overlap
        self.base = kwargs.base
        self.head = kwargs.head
        self.diff = kwargs.diff
        self.chunking_method = kwargs.chunking_method

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            # TODO: git diff here?
            self.input = GitRemote(
                self.config,
                url=path_or_url,
                globs=globs,
                limit=limit,
                prefix="fraim_scan_",
                exclude_globs=exclude_globs,
                paths=paths,
            )
            self.project_path = self.input.root_path()
        else:
            # Fully resolve the path to the project
            self.project_path = os.path.abspath(path_or_url)
            self.repo_name = os.path.basename(self.project_path)
            if self.diff:
                self.input = GitDiff(
                    self.config,
                    self.project_path,
                    head=self.head,
                    base=self.base,
                    globs=globs,
                    limit=limit,
                    exclude_globs=exclude_globs,
                )
            else:
                self.input = Local(
                    self.config,
                    self.project_path,
                    globs=globs,
                    limit=limit,
                    exclude_globs=exclude_globs,
                    paths=paths,
                )

        chunker_class = get_chunking_class(self.chunking_method)

        self.chunker = chunker_class(
            input=self.input,
            project_path=self.project_path,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            model=self.config.model,
            logger=self.config.logger,
        )

    def __iter__(self) -> Iterator[Contextual[str]]:
        return iter(self.chunker)


def get_chunking_class(chunking_method: str) -> type[Chunker]:
    try:
        return CHUNKING_METHODS[chunking_method]
    except KeyError:
        raise ValueError(f"Unsupported chunking method: {chunking_method}")
