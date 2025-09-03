# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Types

Pydantic models and dataclasses for infrastructure discovery workflow.
"""

from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel, Field

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.workflows import ChunkWorkflowInput


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
        description="Type of infrastructure component: api_gateway|load_balancer|database|cache|queue|storage|cdn|proxy|compute|serverless_function|monitoring|network_security|dns|scheduler|security_policy|other"
    )
    provider: str = Field(description="Cloud provider or platform: aws|azure|gcp|on_premise|other")
    service_name: str = Field(description="Specific service name (e.g., RDS, Redis, S3, CloudFront)")
    configuration: str = Field(description="Configuration details or settings for the component")
    discovery_method: str = Field(
        description="How the infrastructure was discovered: concrete|inferred", default="concrete"
    )
    file_source: str | None = Field(
        default=None, description="Specific file where this infrastructure component is defined"
    )
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

    discovery_method_filter: Annotated[
        str | None,
        {
            "help": "Filter by discovery method: 'concrete' (only explicitly defined), 'inferred' (only referenced), or None (both)"
        },
    ] = "concrete"

    intelligent_test_detection: Annotated[
        bool, {"help": "Use LLM-based intelligent test file detection to exclude test files during processing"}
    ] = True


@dataclass
class AgentInput:
    """Input for analyzing a single infrastructure chunk."""

    code: CodeChunk
    config: Config
    focus_environments: list[str] | None = None
    include_secrets: bool = True
