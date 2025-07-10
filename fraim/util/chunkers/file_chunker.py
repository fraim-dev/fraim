import os
import tempfile
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.file_chunks import chunk_input
from fraim.inputs.files import Files
from fraim.inputs.git import Git
from fraim.inputs.local import Local


def generate_file_chunks(
    config: Config, files: Files, project_path: str, chunk_size: int
) -> Generator[CodeChunk, None, None]:
    for file in files:
        config.logger.info(f"Generating chunks for file: {file.path}")
        chunked = chunk_input(file, project_path, chunk_size)
        for chunk in chunked:
            yield chunk


def get_files(
    limit: Optional[int], repo: Optional[str], path: Optional[str], globs: List[str], config: Config
) -> Tuple[str, Files]:
    """Get the local root path of the project and the files to scan."""
    config.logger.info(f"Using file patterns: {globs}")
    if limit is not None:
        # TODO: enforce this
        config.logger.info(f"File limit set to {limit}")
    if repo and path:
        raise ValueError("Repo and path cannot be specified at the same time.")
    if repo:
        temp_dir = tempfile.mkdtemp(prefix="fraim_scan_")
        repo_path = os.path.join(temp_dir, "repo")
        config.logger.info(f"Cloning repository: {repo} into path: {repo_path}")
        return repo_path, Git(config, url=repo, tempdir=repo_path, globs=globs, limit=limit)
    elif path:
        repo_path = path
        config.logger.info(f"Using local path as input: {path}")
        return repo_path, Local(config, Path(repo_path), globs=globs, limit=limit)
    else:
        raise ValueError("Repo or path must be specified.")
