# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from collections.abc import Iterator
from types import TracebackType

from git import Repo
from unidiff import PatchSet

from fraim.core.contextuals import CodeChunk
from fraim.inputs.input import Input


# TODO: Git remote input? Wrap git input?
class GitDiff(Input):
    def __init__(
        self,
        path: str,
        head: str | None,
        base: str | None,
        globs: list[str] | None = None,
        limit: int | None = None,
    ):
        self.globs = globs
        self.limit = limit
        self.path = path
        self.head = head
        self.base = base

    def __enter__(self) -> "GitDiff":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return None

    def root_path(self) -> str:
        return self.path

    def _git_repo(self) -> Repo:
        return Repo(self.path)

    # TODO: Can we iterate repo.git.diff directly?
    def _git_diff(self, repo: Repo) -> str:
        return str(repo.git.diff(self.base, self.head))

    def __iter__(self) -> Iterator[CodeChunk]:
        repo = self._git_repo()
        diff = self._git_diff(repo)

        # Parse the diff output
        # TODO: could we use the entire file's unified diff as the chunk?
        patch_set = PatchSet(diff)
        for patched_file in patch_set:
            for hunk in patched_file:
                unified = str(hunk)
                line_start_incl = hunk.target_start  # TODO: implement this correctly
                line_end_incl = hunk.target_start + hunk.target_length - 1  # TODO: implement this correctly

                yield CodeChunk(
                    file_path=patched_file.path,
                    content=unified,
                    line_number_start_inclusive=line_start_incl,
                    line_number_end_inclusive=line_end_incl,
                )
