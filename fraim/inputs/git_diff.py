# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path
from typing import Iterator, List, Optional, Type
from git import Repo
from unidiff import PatchSet
from fraim.config.config import Config
from fraim.inputs.files import File, Files


class GitDiff(Files):
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

    def __iter__(self) -> Iterator[File]:
        repo = Repo(self.path)

        # Get the raw diff output
        diff_output = repo.git.diff() # TODO: base, head ?
        if not diff_output.strip():
            return

        # Parse the diff output, yield File(path, hunk_text) for each hunk
        patch_set = PatchSet(diff_output)
        for patched_file in patch_set:
            for hunk in patched_file:
                # Use the actual line header as provided by the hunk (better than reconstructing manually)
                hunk_lines = [str(hunk)]
                hunk_lines.extend(line.value.rstrip("\n") for line in hunk)
                yield File(Path(patched_file.path), "\n".join(hunk_lines))