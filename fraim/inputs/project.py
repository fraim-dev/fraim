import os
from collections.abc import Iterator
from typing import Any, Literal

from fraim.core.contextuals import Contextual
from fraim.inputs.chunkers import FileChunker, FixedTokenChunker, MaxContextChunker
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.chunkers.original import OriginalChunker
from fraim.inputs.chunkers.packed_fixed import PackingFixedTokenChunker, PackingSyntacticChunker
from fraim.inputs.chunkers.syntactic import SyntacticChunker
from fraim.inputs.git import GitRemote
from fraim.inputs.git_diff import GitDiff
from fraim.inputs.input import Input
from fraim.inputs.local import Local
from fraim.inputs.status_check import StatusCheck

CHUNKING_METHODS = {
    "syntactic": SyntacticChunker,
    "fixed_token": FixedTokenChunker,
    "packed": PackingSyntacticChunker,
    "packed_fixed": PackingFixedTokenChunker,
    "file": FileChunker,
    "project": MaxContextChunker,
    "original": OriginalChunker,
}


class ProjectInput:
    input: Input
    chunk_size: int
    project_path: str
    repo_name: str
    chunking_method: Literal["syntactic", "fixed", "fixed_token", "packed", "file", "project", "original"] = "original"

    # TODO: **kwargs?
    def __init__(self, kwargs: Any) -> None:
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
        self.status_check = getattr(kwargs, "status_check", None)
        self.chunking_method = kwargs.chunking_method
        self.model = kwargs.model

        if path_or_url is None:
            raise ValueError("Location is required")

        if path_or_url.startswith("http://") or path_or_url.startswith("https://") or path_or_url.startswith("git@"):
            self.repo_name = path_or_url.split("/")[-1].replace(".git", "")
            # TODO: git diff here?
            self.input = GitRemote(
                url=path_or_url,
                globs=globs,
                limit=limit,
                prefix="fraim_scan_",
                exclude_globs=exclude_globs,
                paths=paths,
            )
            self.project_path = self.input.root_path
        else:
            # Fully resolve the path to the project
            self.project_path = os.path.abspath(path_or_url)
            self.repo_name = os.path.basename(self.project_path)
            if self.diff:
                self.input = GitDiff(
                    path=self.project_path,
                    head=self.head,
                    base=self.base,
                    globs=globs,
                    limit=limit,
                    exclude_globs=exclude_globs,
                )
            elif self.status_check:
                self.input = StatusCheck(self.project_path)
            else:
                self.input = Local(
                    root_path=self.project_path,
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
            model=self.model,
        )

    def __iter__(self) -> Iterator[Contextual[str]]:
        return iter(self.chunker)


def get_chunking_class(chunking_method: str) -> type[Chunker]:
    try:
        return CHUNKING_METHODS[chunking_method]
    except KeyError:
        raise ValueError(f"Unsupported chunking method: {chunking_method}")
