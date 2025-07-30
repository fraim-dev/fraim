# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Workflow

Analyzes infrastructure and deployment configurations to identify container configurations,
orchestration patterns, scaling policies, and deployment strategies.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_json_output

# Infrastructure-focused file patterns
INFRASTRUCTURE_FILE_PATTERNS = [
    # Infrastructure & Container files
    "Dockerfile",
    ".dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.k8s.yaml",
    "*.k8s.yml",
    "deployment.yaml",
    "service.yaml",
    "ingress.yaml",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "terraform.tfstate",
    # Infrastructure Configuration files
    "*.yaml",
    "*.yml",
    "*.json",
    "*.toml",
    "*.ini",
    "*.conf",
    "*.config",
    "*.properties",
    "*.env",
    ".env*",
    "*.settings",
    # Build & Package files (reveal deployment structure)
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
    "Makefile",
    "makefile",
    "*.mk",
    # Orchestration and CI/CD files
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    "skaffold.yaml",
    "helm/**/*.yaml",
    "helm/**/*.yml",
]

# Load infrastructure prompts
INFRASTRUCTURE_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "infrastructure_prompts.yaml")
)


# Pydantic models for Infrastructure Analysis
class EnvironmentVariable(BaseModel):
    name: str
    value: Optional[str] = None
    is_secret: bool


class ResourceLimits(BaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None
    storage: Optional[str] = None


class ContainerConfig(BaseModel):
    container_name: str
    base_image: str
    exposed_ports: List[int]
    environment_variables: List[EnvironmentVariable]
    volume_mounts: List[str]
    resource_limits: ResourceLimits
    confidence: float


class InfrastructureAnalysisResult(BaseModel):
    container_configs: List[ContainerConfig]
    infrastructure_components: List[Dict[str, Any]]
    deployment_environments: List[Dict[str, Any]]


@dataclass
class InfrastructureDiscoveryInput(ChunkWorkflowInput):
    """Input for the Infrastructure Discovery workflow."""

    focus_environments: Annotated[
        Optional[List[str]], {"help": "Specific environments to focus on (e.g., production, staging, development)"}
    ] = None

    include_secrets: Annotated[bool, {"help": "Include analysis of environment variables and secrets"}] = True


@dataclass
class AgentInput:
    """Input for analyzing a single infrastructure chunk."""

    file_path: str
    content: str
    config: Config


@workflow("infrastructure_discovery")
class InfrastructureDiscoveryWorkflow(ChunkProcessingMixin, Workflow[InfrastructureDiscoveryInput, Dict[str, Any]]):
    """
    Analyzes infrastructure and deployment configurations to extract:
    - Container configurations and orchestration patterns
    - Scaling policies and resource management
    - Deployment strategies and environments
    - Infrastructure components and their relationships
    - Runtime and operational characteristics
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Initialize LLM and infrastructure analysis step
        self.llm = LiteLLM.from_config(self.config)

        # Infrastructure analysis step
        infrastructure_parser = PydanticOutputParser(InfrastructureAnalysisResult)
        self.infrastructure_step: LLMStep[AgentInput, InfrastructureAnalysisResult] = LLMStep(
            self.llm, INFRASTRUCTURE_PROMPTS["system"], INFRASTRUCTURE_PROMPTS["user"], infrastructure_parser
        )

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for infrastructure discovery."""
        return INFRASTRUCTURE_FILE_PATTERNS

    async def _process_single_chunk(
        self, chunk: CodeChunk, focus_environments: Optional[List[str]] = None, include_secrets: bool = True
    ) -> List[InfrastructureAnalysisResult]:
        """Process a single chunk for infrastructure analysis."""
        try:
            self.config.logger.debug(f"Processing infrastructure chunk: {Path(chunk.file_path)}")

            chunk_input = AgentInput(
                file_path=chunk.file_path,
                content=chunk.content,
                config=self.config,
            )

            # Run infrastructure analysis
            result = await self.infrastructure_step.run(chunk_input)
            return [result]

        except Exception as e:
            self.config.logger.error(
                f"Failed to process infrastructure chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return []

    async def _aggregate_results(self, chunk_results: List[InfrastructureAnalysisResult]) -> Dict[str, Any]:
        """Aggregate infrastructure results from multiple chunks."""

        if not chunk_results:
            self.config.logger.warning("No infrastructure chunks processed successfully")
            return {
                "container_configs": [],
                "infrastructure_components": [],
                "deployment_environments": [],
                "confidence_score": 0.0,
                "analysis_summary": "No infrastructure files found or processed",
                "files_analyzed": 0,
                "total_chunks_processed": 0,
            }

        # Aggregate all results
        all_container_configs = []
        all_infrastructure_components = []
        all_deployment_environments = []

        for result in chunk_results:
            all_container_configs.extend(result.container_configs)
            all_infrastructure_components.extend(result.infrastructure_components)
            all_deployment_environments.extend(result.deployment_environments)

        # Simple deduplication by name/identifier
        unique_containers = self._deduplicate_containers(all_container_configs)
        unique_components = self._deduplicate_components(all_infrastructure_components)
        unique_environments = self._deduplicate_environments(all_deployment_environments)

        # Calculate confidence based on number of files and quality of findings
        confidence_score = min(0.9, 0.4 + (len(chunk_results) * 0.1) + (len(unique_containers) * 0.05))

        analysis_summary = self._create_infrastructure_summary(
            unique_containers, unique_components, unique_environments, len(chunk_results)
        )

        return {
            "container_configs": [config.model_dump() for config in unique_containers],
            "infrastructure_components": unique_components,
            "deployment_environments": unique_environments,
            "confidence_score": confidence_score,
            "analysis_summary": analysis_summary,
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results),
        }

    def _deduplicate_containers(self, containers: List[ContainerConfig]) -> List[ContainerConfig]:
        """Remove duplicate container configurations."""
        seen = set()
        unique = []
        for container in containers:
            # Use container name and base image as deduplication key
            key = f"{container.container_name}:{container.base_image}"
            if key not in seen:
                seen.add(key)
                unique.append(container)
        return unique

    def _deduplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate infrastructure components."""
        seen = set()
        unique = []
        for component in components:
            # Use component name/type as deduplication key
            key = f"{component.get('name', 'unknown')}:{component.get('type', 'unknown')}"
            if key not in seen:
                seen.add(key)
                unique.append(component)
        return unique

    def _deduplicate_environments(self, environments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate deployment environments."""
        seen = set()
        unique = []
        for env in environments:
            # Use environment name as deduplication key
            key = env.get("name", "unknown")
            if key not in seen:
                seen.add(key)
                unique.append(env)
        return unique

    def _create_infrastructure_summary(
        self,
        containers: List[ContainerConfig],
        components: List[Dict[str, Any]],
        environments: List[Dict[str, Any]],
        files_analyzed: int,
    ) -> str:
        """Create a human-readable summary of the infrastructure analysis."""

        summary_parts = [f"Analyzed {files_analyzed} infrastructure files."]

        if containers:
            summary_parts.append(f"Found {len(containers)} container configurations.")
            base_images = set(c.base_image for c in containers if c.base_image)
            if base_images:
                summary_parts.append(f"Base images: {', '.join(list(base_images)[:3])}")
                if len(base_images) > 3:
                    summary_parts[-1] += f" and {len(base_images) - 3} others"

        if components:
            summary_parts.append(f"Identified {len(components)} infrastructure components.")

        if environments:
            env_names = [env.get("name", "unknown") for env in environments]
            summary_parts.append(f"Deployment environments: {', '.join(env_names[:3])}")
            if len(env_names) > 3:
                summary_parts[-1] += f" and {len(env_names) - 3} others"

        return " ".join(summary_parts)

    async def workflow(self, input: InfrastructureDiscoveryInput) -> Dict[str, Any]:
        """Main Infrastructure Discovery workflow."""
        try:
            self.config.logger.info("Starting Infrastructure Discovery workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # 2. Create a closure that captures workflow parameters
            async def chunk_processor(chunk: CodeChunk) -> List[InfrastructureAnalysisResult]:
                return await self._process_single_chunk(chunk, input.focus_environments, input.include_secrets)

            # 3. Process chunks concurrently using mixin utility
            chunk_results = await self.process_chunks_concurrently(
                project=project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
            )

            # 4. Aggregate results
            final_result = await self._aggregate_results(chunk_results)

            self.config.logger.info(
                f"Infrastructure Discovery completed. Analyzed {final_result['files_analyzed']} files. "
                f"Confidence: {final_result['confidence_score']:.2f}"
            )

            # 5. Write output file if output_dir is configured
            write_json_output(results=final_result, workflow_name="infrastructure_discovery", config=self.config)

            return final_result

        except Exception as e:
            self.config.logger.error(f"Error during infrastructure discovery: {str(e)}")
            raise e
