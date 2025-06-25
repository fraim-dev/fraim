# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure as Code (IaC) Security Analysis Workflow

Analyzes IaC files (Terraform, CloudFormation, Kubernetes, Docker, etc.)
for security misconfigurations and compliance issues.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from fraim.config import Config
from fraim.core.contextuals import CodeChunk, Contextual
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.outputs import sarif
from fraim.workflows.registry import workflow

FILE_PATTERNS = [
    "*.tf",
    "*.tfvars",
    "*.tfstate",
    "*.yaml",
    "*.yml",
    "*.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.k8s.yaml",
    "*.k8s.yml",
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

    code: CodeChunk
    config: Config


type IaCOutput = List[sarif.Result]


@workflow("iac", file_patterns=FILE_PATTERNS)
class IaCWorkflow(Workflow[IaCInput, IaCOutput]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the Scanner Step
        scanner_llm = llm
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[IaCInput, sarif.RunResults] = LLMStep(
            scanner_llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

    async def workflow(self, input: IaCInput) -> IaCOutput:
        # TODO: See comments on `is_iac_file below.
        # If this chunk is not from an IaC file, don't scan it.
        if not _is_iac_file(Path(input.code.file_path)):
            logging.getLogger().info("File chunk is not from an IaC file - skipping")
            return []

        # 1. Scan the code for vulnerabilities.
        logging.getLogger().info(f"Scanning code for vulnerabilities: {Path(input.code.file_path)}")
        iac_input = IaCInput(code=input.code, config=input.config)
        vulns = await self.scanner_step.run(iac_input)

        # 2. Filter the vulnerability by confidence.
        logging.getLogger().info("Filtering vulnerabilities by confidence")
        high_confidence_vulns = filter_results_by_confidence(vulns.results, input.config.confidence)

        return high_confidence_vulns


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]


# TODO: replace this an LLM step that determines if the file is an IaC file.
# This will require that file iteration and chunking be integrated into the workflow.
def _is_iac_file(filepath: Path) -> bool:
    """Check if the file is an Infrastructure as Code file."""
    iac_extensions = {
        # Terraform
        ".tf",
        ".tfvars",
        ".tfstate",
        # CloudFormation
        ".yaml",
        ".yml",
        ".json",
        # Kubernetes
        ".k8s.yaml",
        ".k8s.yml",
        # Docker
        "Dockerfile",
        ".dockerfile",
        # Ansible
        ".ansible.yaml",
        ".ansible.yml",
        # Helm
        ".helm.yaml",
        ".helm.yml",
    }

    iac_filenames = {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "k8s.yaml",
        "k8s.yml",
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
    }

    # Check if it's a known IaC file
    if filepath.name in iac_filenames:
        return True

    # Check for IaC file extensions
    if filepath.suffix in iac_extensions:
        return True

    # Check for CloudFormation templates (JSON/YAML with specific patterns)
    if filepath.suffix in (".yaml", ".yml", ".json"):
        # Additional logic could be added here to detect CloudFormation
        # by checking content patterns
        return True

    return False
