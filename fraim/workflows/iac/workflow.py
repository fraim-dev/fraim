# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure as Code (IaC) Security Analysis Workflow

Analyzes IaC files (Terraform, CloudFormation, Kubernetes, Docker, etc.)
for security misconfigurations and compliance issues.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.inputs.project import ProjectInput
from fraim.outputs import sarif
from fraim.util.sarif.write_sarif_report import write_sarif_report
from fraim.workflows.registry import workflow

FILE_PATTERNS = [
    "*.tf",
    "*.tfvars",
    "*.tfstate",
    "*.yaml",
    "*.yml",
    "*.json",
    "Dockerfile",
    ".dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.k8s.yaml",
    "*.k8s.yml",
    "*.ansible.yaml",
    "*.ansible.yml",
    "*.helm.yaml",
    "*.helm.yml",
    "deployment.yaml",
    "deployment.yml",
    "service.yaml",
    "service.yml",
    "ingress.yaml",
    "ingress.yml",
    "configmap.yaml",
    "configmap.yml",
    "secret.yaml",
    "secret.yml",
]

SCANNER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "scanner_prompts.yaml"))


@dataclass
class IaCInput:
    """Input for the IaC workflow."""

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


@dataclass
class IaCCodeChunkInput:
    """Input for the IaC workflow."""

    code: CodeChunk
    config: Config


type IaCOutput = List[sarif.Result]


@workflow("iac", file_patterns=FILE_PATTERNS)
class IaCWorkflow(Workflow[IaCInput, IaCOutput]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the Scanner Step
        scanner_llm = llm
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[IaCCodeChunkInput, sarif.RunResults] = LLMStep(
            scanner_llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

    async def workflow(self, input: IaCInput) -> IaCOutput:
        config = self.config
        results: List[sarif.Result] = []

        try:
            kwargs = SimpleNamespace(
                location=input.repo or input.path, globs=input.globs, limit=input.limit, chunk_size=input.chunk_size
            )
            project = ProjectInput(config=config, kwargs=kwargs)
            # Hack to pass in the project path to the config
            config.project_path = project.project_path
            for chunk in project:
                # 1. Scan the code for vulnerabilities.
                self.config.logger.info(f"Scanning code for vulnerabilities: {Path(chunk.file_path)}")
                iac_input = IaCCodeChunkInput(code=chunk, config=input.config)
                vulns = await self.scanner_step.run(iac_input)

                # 2. Filter the vulnerability by confidence.
                self.config.logger.info("Filtering vulnerabilities by confidence")
                high_confidence_vulns = filter_results_by_confidence(vulns.results, input.config.confidence)

                results.extend(high_confidence_vulns)

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


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]
