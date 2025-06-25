# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import multiprocessing as mp
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from fraim.config.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.file_chunks import chunk_input
from fraim.inputs.files import File, Files
from fraim.inputs.git import Git
from fraim.inputs.local import Local
from fraim.observability import ObservabilityManager
from fraim.outputs import sarif
from fraim.reporting.reporting import Reporting
from fraim.workflows import WorkflowRegistry


@dataclass
class ScanArgs:
    """Typed dataclass for all fetch arguments with defaults."""

    repo: Optional[str] = None
    path: Optional[str] = None
    workflows: Optional[List[str]] = None
    globs: Optional[List[str]] = None
    limit: Optional[int] = None

    def __post_init__(self) -> None:
        """Set default values for mutable fields."""
        if self.workflows is None:
            self.workflows = ["all"]


def resolve_workflows(args: ScanArgs) -> List[str]:
    # Handle 'all' workflows and convert to the expected format
    if args.workflows and "all" in args.workflows:
        # Get all available workflows from registry
        return WorkflowRegistry.get_available_workflows()
    elif args.workflows:
        # Filter out 'all' if mixed with other workflows and convert to strings
        return [w for w in args.workflows if w != "all"]

    raise ValueError("No workflows specified")


# Use module-specific globs if available, otherwise fall back to provided globs
def resolve_file_patterns(args: ScanArgs) -> List[str]:
    if args.globs:
        return args.globs
    else:
        return WorkflowRegistry.get_file_patterns_for_workflows(resolve_workflows(args))


def get_files(args: ScanArgs, config: Config) -> Tuple[str, Files]:
    """Get the local root path of the project and the files to scan."""
    file_patterns = resolve_file_patterns(args)
    config.logger.info(f"Using file patterns: {file_patterns}")
    if args.limit is not None:
        config.logger.info(f"File limit set to {args.limit}")  # TODO: enforce this
    if args.repo:
        temp_dir = tempfile.mkdtemp(prefix="fraim_scan_")
        repo_path = os.path.join(temp_dir, "repo")
        config.logger.info(f"Cloning repository: {args.repo} into path: {repo_path}")
        return repo_path, Git(config, url=args.repo, tempdir=repo_path, globs=file_patterns, limit=args.limit)
    elif args.path:
        repo_path = args.path
        config.logger.info(f"Using local path as input: {args.path}")
        return repo_path, Local(config, Path(repo_path), globs=file_patterns, limit=args.limit)
    else:
        raise ValueError("No input specified")


def scan(args: ScanArgs, config: Config, observability_backends: Optional[List[str]] = None) -> List[sarif.Result]:
    results: List[sarif.Result] = []

    # Determine workflows to run
    workflows_to_run = resolve_workflows(args)

    #######################################
    # Run LLM Workflows
    #######################################
    config.logger.info(f"Running workflows: {workflows_to_run}")
    try:
        project_path, files_context = get_files(args, config)
        config.project_path = project_path  # Hack to pass in the project path to the config

        # Process chunks in parallel as they become available (streaming)
        with files_context as files:
            chunks = generate_file_chunks(config, files=files, project_path=project_path, chunk_size=config.chunk_size)
            try:
                chunk_count = 0
                with mp.Pool(
                    processes=config.processes, initializer=initialize_worker, initargs=(config, observability_backends)
                ) as pool:
                    # This must be partial because mp serializes the function.
                    # TODO: actually test that multiprocessing has a measurable impact here.
                    task = partial(run_workflows, config=config, workflows_to_run=workflows_to_run)

                    for chunk_results in pool.imap_unordered(task, chunks):
                        chunk_count += 1
                        results.extend(chunk_results)
                config.logger.info(f"Completed processing {chunk_count} total chunks")
            except Exception as mp_error:
                config.logger.error(f"Error during multiprocessing: {str(mp_error)}")

    except Exception as e:
        config.logger.error(f"Error during scan: {str(e)}")
        raise e

    #######################################
    # Output Results
    #######################################
    # Generate the SARIF report
    report = sarif.create_sarif_report(results)

    repo_name = "Security Scan Report"
    if args.repo:
        repo_name = args.repo.split("/")[-1].replace(".git", "")
    elif args.path:
        repo_name = os.path.basename(os.path.abspath(args.path))

    # Create filename with sanitized repo name
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize repo name for filename (replace spaces and special chars with underscores)
    safe_repo_name = "".join(c if c.isalnum() else "_" for c in repo_name).strip("_")
    sarif_filename = f"fraim_report_{safe_repo_name}_{current_time}.sarif"
    html_filename = f"fraim_report_{safe_repo_name}_{current_time}.html"

    sarif_output_file = os.path.join(config.scan_dir, sarif_filename)
    html_output_file = os.path.join(config.scan_dir, html_filename)

    total_results = len(results)

    # Write SARIF JSON file
    try:
        with open(sarif_output_file, "w") as f:
            f.write(report.model_dump_json(indent=2))
        config.logger.info(f"Wrote SARIF report ({total_results} results) to {sarif_output_file}")
    except Exception as e:
        config.logger.error(f"Failed to write SARIF report to {sarif_output_file}: {str(e)}")
    # Write HTML report file (independent of SARIF write)
    try:
        Reporting.generate_html_report(sarif_report=report, repo_name=repo_name, output_path=html_output_file)
        config.logger.info(f"Wrote HTML report ({total_results} results) to {html_output_file}")
    except Exception as e:
        config.logger.error(f"Failed to write HTML report to {html_output_file}: {str(e)}")
    return results


def generate_file_chunks(
    config: Config, files: Files, project_path: str, chunk_size: int
) -> Generator[CodeChunk, None, None]:
    for file in files:
        config.logger.info(f"Generating chunks for file: {file.path}")
        chunked = chunk_input(file, project_path, chunk_size)
        for chunk in chunked:
            yield chunk


def initialize_worker(config: Config, observability_backends: Optional[List[str]]) -> None:
    """Initialize worker process with observability setup."""
    if observability_backends:
        try:
            manager = ObservabilityManager(observability_backends, logger=config.logger)
            manager.setup()
        except Exception as e:
            config.logger.warning(f"Failed to setup observability in worker process: {str(e)}")


def run_workflows(code_chunk: CodeChunk, config: Config, workflows_to_run: List[str]) -> List[sarif.Result]:
    """Run all specified workflows on the given data."""
    all_results = []
    for workflow in workflows_to_run:
        try:
            if WorkflowRegistry.is_workflow_available(workflow):
                results = WorkflowRegistry.execute_workflow(workflow, code=code_chunk, config=config)
                all_results.extend(results)
            else:
                config.logger.warning(f"Workflow '{workflow}' not available in registry")
        except Exception as e:
            config.logger.error(f"Error running {workflow} workflow on {code_chunk.description}: {str(e)}")
            continue

    return all_results
