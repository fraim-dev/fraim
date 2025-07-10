# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Application Security Analysis Workflow

Analyzes application configurations and deployment files for security vulnerabilities.
"""

import os
from dataclasses import dataclass
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.workflows import Workflow
from fraim.outputs import sarif
from fraim.util.chunkers.file_chunker import generate_file_chunks, get_files
from fraim.util.repo.run_workflows_on_chunks import run_parallel_workflows_on_chunks
from fraim.util.sarif.write_sarif_report import write_sarif_report
from fraim.workflows.registry import workflow

FILE_PATTERNS = [
    "*.yml",
    "*.yaml",
    "*.json",
    "*.toml",
    "*.ini",
    "*.cfg",
    "*.conf",
    "*.properties",
    "*.xml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "*.k8s.yml",
    "*.k8s.yaml",
    "*.helm",
    "requirements.txt",
    "package.json",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "Cargo.toml",
    "go.mod",
    "composer.json",
]

WORKFLOWS_TO_RUN = ["code"]


@dataclass
class ApplicationInput:
    """Input for the Application workflow."""

    config: Config
    processes: Annotated[int, {"help": "Number of processes to use"}]
    # File processing
    chunk_size: Annotated[int, {"help": "Number of lines per chunk"}] = 500
    limit: Annotated[Optional[int], {"help": "Limit the number of files to scan"}] = None
    repo: Annotated[Optional[str], {"help": "Repository URL to scan"}] = None
    path: Annotated[Optional[str], {"help": "Local path to scan"}] = None
    globs: Annotated[
        Optional[List[str]],
        {"help": "Globs to use for file scanning. If not provided, will use file_patterns defined in the workflow."},
    ] = None


type ApplicationOutput = List[sarif.Result]


@workflow("application", file_patterns=FILE_PATTERNS)
class ApplicationWorkflow(Workflow[ApplicationInput, ApplicationOutput]):
    """Analyzes application configurations and deployment files for security vulnerabilities"""

    def __init__(
        self, config: Config, *args: Any, observability_backends: Optional[List[str]] = None, **kwargs: Any
    ) -> None:
        self.config = config
        self.observability_backends = observability_backends

    async def workflow(self, input: ApplicationInput) -> ApplicationOutput:
        config = self.config
        results: List[sarif.Result] = []

        try:
            project_path, files_context = get_files(
                limit=input.limit, repo=input.repo, path=input.path, globs=input.globs or FILE_PATTERNS, config=config
            )
            # Hack to pass in the project path to the config
            config.project_path = project_path

            # Process chunks in parallel as they become available (streaming)
            with files_context as files:
                chunks = generate_file_chunks(
                    config, files=files, project_path=project_path, chunk_size=input.chunk_size
                )
                results.extend(
                    run_parallel_workflows_on_chunks(
                        chunks=chunks,
                        config=config,
                        workflows_to_run=WORKFLOWS_TO_RUN,
                        observability_backends=self.observability_backends,
                        processes=input.processes,
                    )
                )

        except Exception as e:
            config.logger.error(f"Error during scan: {str(e)}")
            raise e

        repo_name = "Security Scan Report"
        if input.repo:
            repo_name = input.repo.split("/")[-1].replace(".git", "")
        elif input.path:
            repo_name = os.path.basename(os.path.abspath(input.path))

        write_sarif_report(results=results, repo_name=repo_name, config=config)

        return results
