from typing import Generator, List, Tuple
import tempfile
import os
from pathlib import Path

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.git import Git
from fraim.inputs.local import Local
from fraim.inputs.files import Files
from fraim.inputs.file_chunks import chunk_input
from fraim.scan import ScanArgs
from fraim.workflows import WorkflowRegistry


def generate_file_chunks(
    config: Config, files: Files, project_path: str, chunk_size: int
) -> Generator[CodeChunk, None, None]:
    for file in files:
        config.logger.info(f"Generating chunks for file: {file.path}")
        chunked = chunk_input(file, project_path, chunk_size)
        for chunk in chunked:
            yield chunk

# Use module-specific globs if available, otherwise fall back to provided globs

# Use module-specific globs if available, otherwise fall back to provided globs
def resolve_file_patterns(args: ScanArgs) -> List[str]:
    if args.globs:
        return args.globs
    else:
        return WorkflowRegistry.get_file_patterns_for_workflows(args.workflows)


def get_files(args: ScanArgs, config: Config) -> Tuple[str, Files]:
    """Get the local root path of the project and the files to scan."""
    file_patterns = resolve_file_patterns(args)
    config.logger.info(f"Using file patterns: {file_patterns}")
    if args.limit is not None:
        # TODO: enforce this
        config.logger.info(f"File limit set to {args.limit}")
    if args.repo:
        temp_dir = tempfile.mkdtemp(prefix="fraim_scan_")
        repo_path = os.path.join(temp_dir, "repo")
        config.logger.info(
            f"Cloning repository: {args.repo} into path: {repo_path}")
        return repo_path, Git(config, url=args.repo, tempdir=repo_path, globs=file_patterns, limit=args.limit)
    elif args.path:
        repo_path = args.path
        config.logger.info(f"Using local path as input: {args.path}")
        return repo_path, Local(config, Path(repo_path), globs=file_patterns, limit=args.limit)
    else:
        raise ValueError("No input specified")

