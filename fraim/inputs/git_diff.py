# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path
from typing import Iterator, List, Optional, Type
from git import Repo
from unidiff import PatchSet
from fraim.config.config import Config
from fraim.inputs.file import File
from fraim.inputs.input import Input

class GitDiff(Input):
    def __init__(self, config: Config, path: Path, globs: Optional[List[str]] = None, limit: Optional[int] = None):
        self.config = config
        self.globs = globs
        self.limit = limit
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def root_path(self) -> str:
        return self.path.name

    def _git_repo(self) -> Repo:
        return Repo(self.path)

    def _git_diff(self, repo: Repo) -> str:
        head = self.config.git_head or repo.head.commit
        if self.config.git_base:
            return repo.git.diff(self.config.git_base, head)
        else:
            return repo.git.diff(head)

    def __iter__(self) -> Iterator[File]:
        repo = self._git_repo()
        diff = self._git_diff(repo)

        # Parse the diff output
        patch_set = PatchSet(diff)
        for patched_file in patch_set:
            for hunk in patched_file:
                body = str(hunk)
                yield File(Path(patched_file.path), body)
                         # + "\n") # Header, like: @@ -12,7 +12,7 @@
                # body = body + "".join([str(line) for line in hunk]) # "@@ -12,7 +12,7 @@\n- old line\n+ new line\n"
                # yield File(Path(patched_file.path), body)

