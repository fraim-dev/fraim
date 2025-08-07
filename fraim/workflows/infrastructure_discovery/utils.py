# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Utilities

Helper functions for infrastructure discovery workflow.
"""

from .types import ContainerConfig, DeploymentEnvironment, InfrastructureComponent


def create_infrastructure_summary(
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
