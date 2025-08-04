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
from typing import Annotated, Any

from pydantic import BaseModel, Field

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
INFRASTRUCTURE_PROMPTS = PromptTemplate.from_yaml(str(Path(__file__).parent / "infrastructure_prompts.yaml"))


# Pydantic models for Infrastructure Analysis
class EnvironmentVariable(BaseModel):
    name: str = Field(description="The name of the environment variable")
    value: str | None = Field(
        default=None, description="The value of the environment variable (may be None for secrets)"
    )
    is_secret: bool = Field(description="Whether this environment variable contains sensitive information")


class ResourceLimits(BaseModel):
    cpu: str | None = Field(default=None, description="CPU resource limit (e.g., '500m', '1', '2.5')")
    memory: str | None = Field(default=None, description="Memory resource limit (e.g., '512Mi', '1Gi', '2Gi')")
    storage: str | None = Field(default=None, description="Storage resource limit (e.g., '10Gi', '100Gi')")


class ContainerConfig(BaseModel):
    container_name: str = Field(description="Name or identifier of the container")
    base_image: str = Field(description="Base Docker image used for the container")
    exposed_ports: list[int] = Field(description="List of ports exposed by the container")
    environment_variables: list[EnvironmentVariable] = Field(
        description="List of environment variables configured for the container"
    )
    volume_mounts: list[str] = Field(description="List of volume mount paths or configurations")
    resource_limits: ResourceLimits = Field(description="Resource limits and requests for the container")
    confidence: float = Field(description="Confidence score (0.0-1.0) for this container configuration analysis")


class InfrastructureComponent(BaseModel):
    name: str = Field(description="Name or identifier of the infrastructure component")
    type: str = Field(
        description="Type of infrastructure component: load_balancer|database|cache|queue|storage|cdn|proxy|other"
    )
    provider: str = Field(description="Cloud provider or platform: aws|azure|gcp|on_premise|other")
    service_name: str = Field(description="Specific service name (e.g., RDS, Redis, S3, CloudFront)")
    configuration: str = Field(description="Configuration details or settings for the component")
    availability_zone: str | None = Field(
        default=None, description="Availability zone or region where the component is deployed"
    )
    backup_strategy: str | None = Field(default=None, description="Backup and disaster recovery strategy")
    monitoring: str | None = Field(default=None, description="Monitoring and alerting configuration")
    confidence: float = Field(description="Confidence score (0.0-1.0) for this component analysis")


class DeploymentEnvironment(BaseModel):
    name: str = Field(description="Environment name: production|staging|development|test|other")
    namespace: str | None = Field(default=None, description="Kubernetes namespace or environment isolation identifier")
    resource_quotas: str | None = Field(default=None, description="Resource quotas and limits for the environment")
    network_policies: list[str] = Field(default_factory=list, description="Network policies and security rules")
    secrets_management: str | None = Field(default=None, description="Secrets management strategy and tools used")
    ingress_config: str | None = Field(default=None, description="Ingress and routing configuration")
    monitoring_config: str | None = Field(default=None, description="Environment-specific monitoring configuration")
    confidence: float = Field(description="Confidence score (0.0-1.0) for this environment analysis")


class InfrastructureAnalysisResult(BaseModel):
    container_configs: list[ContainerConfig]
    infrastructure_components: list[InfrastructureComponent]
    deployment_environments: list[DeploymentEnvironment]


@dataclass
class InfrastructureDiscoveryInput(ChunkWorkflowInput):
    """Input for the Infrastructure Discovery workflow."""

    focus_environments: Annotated[
        list[str] | None, {"help": "Specific environments to focus on (e.g., production, staging, development)"}
    ] = None

    include_secrets: Annotated[bool, {"help": "Include analysis of environment variables and secrets"}] = True


@dataclass
class AgentInput:
    """Input for analyzing a single infrastructure chunk."""

    code: CodeChunk
    config: Config


@workflow("infrastructure_discovery")
class InfrastructureDiscoveryWorkflow(ChunkProcessingMixin, Workflow[InfrastructureDiscoveryInput, dict[str, Any]]):
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
    def file_patterns(self) -> list[str]:
        """File patterns for infrastructure discovery."""
        return INFRASTRUCTURE_FILE_PATTERNS

    async def _process_single_chunk(
        self, chunk: CodeChunk, focus_environments: list[str] | None = None, include_secrets: bool = True
    ) -> list[InfrastructureAnalysisResult]:
        """Process a single chunk for infrastructure analysis."""
        try:
            self.config.logger.debug(f"Processing infrastructure chunk: {Path(chunk.file_path)}")

            chunk_input = AgentInput(
                code=chunk,
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

    async def _aggregate_results(self, chunk_results: list[InfrastructureAnalysisResult]) -> dict[str, Any]:
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
            "infrastructure_components": [component.model_dump() for component in unique_components],
            "deployment_environments": [env.model_dump() for env in unique_environments],
            "confidence_score": confidence_score,
            "analysis_summary": analysis_summary,
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results),
        }

    def _deduplicate_containers(self, containers: list[ContainerConfig]) -> list[ContainerConfig]:
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

    def _deduplicate_components(self, components: list[InfrastructureComponent]) -> list[InfrastructureComponent]:
        """Remove duplicate infrastructure components."""
        seen = set()
        unique = []
        for component in components:
            # Create a tuple of the key identifying fields
            key = (component.name, component.type, component.provider, component.service_name)
            if key not in seen:
                seen.add(key)
                unique.append(component)
        return unique

    def _deduplicate_environments(self, environments: list[DeploymentEnvironment]) -> list[DeploymentEnvironment]:
        """Remove duplicate deployment environments."""
        seen = set()
        unique = []
        for environment in environments:
            # Create a tuple of the key identifying fields
            key = (environment.name, environment.namespace)
            if key not in seen:
                seen.add(key)
                unique.append(environment)
        return unique

    def _create_infrastructure_summary(
        self,
        containers: list[ContainerConfig],
        components: list[InfrastructureComponent],
        environments: list[DeploymentEnvironment],
        files_analyzed: int,
    ) -> str:
        """Create a human-readable summary of the infrastructure analysis."""
        summary_parts = []

        if containers:
            container_names = [c.container_name for c in containers]
            summary_parts.append(f"Containers: {', '.join(container_names[:3])}")
            if len(containers) > 3:
                summary_parts[-1] += f" and {len(containers) - 3} others"

        if components:
            component_types = {c.type for c in components}
            summary_parts.append(f"Infrastructure: {', '.join(sorted(component_types))}")

        if environments:
            env_names = [e.name for e in environments]
            summary_parts.append(f"Environments: {', '.join(env_names)}")

        summary_parts.append(f"Files analyzed: {files_analyzed}")

        return " ".join(summary_parts)

    async def workflow(self, input: InfrastructureDiscoveryInput) -> dict[str, Any]:
        """Main Infrastructure Discovery workflow."""
        try:
            self.config.logger.info("Starting Infrastructure Discovery workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # 2. Create a closure that captures workflow parameters
            async def chunk_processor(chunk: CodeChunk) -> list[InfrastructureAnalysisResult]:
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
