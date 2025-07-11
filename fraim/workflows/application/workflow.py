# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Application Security Analysis Workflow

Analyzes application configurations and deployment files for security vulnerabilities.
"""

import os
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.workflows import Workflow
from fraim.inputs.project import ProjectInput
from fraim.outputs import sarif
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
    # Actual Input
    repo: Annotated[Optional[str], {"help": "Repository URL to scan"}] = None
    path: Annotated[Optional[str], {"help": "Local path to scan"}] = None
    # File processing
    chunk_size: Annotated[int, {"help": "Number of lines per chunk"}] = 500
    limit: Annotated[Optional[int], {"help": "Limit the number of files to scan"}] = None
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
            kwargs = SimpleNamespace(
                location=input.repo or input.path, globs=input.globs, limit=input.limit, chunk_size=input.chunk_size
            )
            project = ProjectInput(config=config, kwargs=kwargs)
            config.project_path = project.project_path

            results.extend(
                run_parallel_workflows_on_chunks(
                    chunks=iter(project),
                    config=config,
                    workflows_to_run=WORKFLOWS_TO_RUN,
                    processes=input.processes,
                    observability_backends=self.observability_backends,
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
