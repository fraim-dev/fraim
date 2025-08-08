# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Synthesis Utils

Common utilities and helper methods for architecture synthesis operations.
"""

from datetime import datetime
from typing import Any, Dict, List

from fraim.config import Config

from .types import ComponentDiscoveryResults


class SynthesisUtils:
    """Utility methods for architecture synthesis operations."""

    def __init__(self, config: Config):
        self.config = config

    def get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        return datetime.utcnow().isoformat()

    def count_discovered_components(self, results: ComponentDiscoveryResults) -> int:
        """Count total discovered components across all discovery types."""
        count = 0

        if results.infrastructure:
            count += self._count_infrastructure_components(results.infrastructure)

        if results.api_interfaces:
            count += self._count_api_components(results.api_interfaces)

        return count

    def _count_infrastructure_components(self, infrastructure: Dict[str, Any]) -> int:
        """Count infrastructure components."""
        count = 0

        # Count deployment topology components
        if "deployment_topology" in infrastructure:
            topology = infrastructure["deployment_topology"]
            for instances in topology.values():
                if isinstance(instances, list):
                    count += len(instances)
                elif isinstance(instances, dict):
                    count += 1

        return count

    def _count_api_components(self, api_interfaces: Dict[str, Any]) -> int:
        """Count API components."""
        count = 0

        # Count API endpoints
        if "api_endpoints" in api_interfaces:
            count += len(api_interfaces["api_endpoints"])

        # Count service contracts
        if "service_contracts" in api_interfaces:
            count += len(api_interfaces["service_contracts"])

        return count

    def validate_discovery_results(self, results: ComponentDiscoveryResults) -> List[str]:
        """Validate discovery results and return list of validation issues."""
        issues = []

        # Check if any discovery was successful
        if not results.infrastructure and not results.api_interfaces:
            issues.append("No discovery results available")

        # Check for infrastructure issues
        if results.infrastructure:
            if "error" in results.infrastructure:
                issues.append(f"Infrastructure discovery error: {results.infrastructure['error']}")
            elif not any(results.infrastructure.values()):
                issues.append("Infrastructure discovery returned empty results")

        # Check for API issues
        if results.api_interfaces:
            if "error" in results.api_interfaces:
                issues.append(f"API discovery error: {results.api_interfaces['error']}")
            elif not any(results.api_interfaces.values()):
                issues.append("API discovery returned empty results")

        return issues

    def extract_unique_components(self, results: ComponentDiscoveryResults) -> List[str]:
        """Extract list of unique component names from discovery results."""
        components = set()

        # Extract from infrastructure
        if results.infrastructure and "deployment_topology" in results.infrastructure:
            topology = results.infrastructure["deployment_topology"]
            for component_type, instances in topology.items():
                if isinstance(instances, list):
                    for instance in instances:
                        if isinstance(instance, dict) and "name" in instance:
                            components.add(instance["name"])
                elif isinstance(instances, dict) and "name" in instances:
                    components.add(instances["name"])

        # Extract from API interfaces
        if results.api_interfaces:
            # Extract service names from endpoints
            if "api_endpoints" in results.api_interfaces:
                for endpoint in results.api_interfaces["api_endpoints"]:
                    if isinstance(endpoint, dict) and "service" in endpoint:
                        components.add(endpoint["service"])

            # Extract from external dependencies
            if "external_api_dependencies" in results.api_interfaces:
                for dep in results.api_interfaces["external_api_dependencies"]:
                    if isinstance(dep, dict) and "name" in dep:
                        components.add(dep["name"])

        return sorted(list(components))

    def create_metadata_summary(
        self, results: ComponentDiscoveryResults, diagram_format: str = "mermaid"
    ) -> Dict[str, Any]:
        """Create comprehensive metadata summary for architecture results."""
        return {
            "analysis_timestamp": self.get_timestamp(),
            "diagram_format": diagram_format,
            "component_count": self.count_discovered_components(results),
            "unique_components": len(self.extract_unique_components(results)),
            "discovery_status": self._get_discovery_status(results),
            "validation_issues": self.validate_discovery_results(results),
            "data_sources": self._identify_data_sources(results),
        }

    def _get_discovery_status(self, results: ComponentDiscoveryResults) -> Dict[str, str]:
        """Get status of each discovery type."""
        status = {}

        if results.infrastructure:
            if "error" in results.infrastructure:
                status["infrastructure"] = "failed"
            elif any(results.infrastructure.values()):
                status["infrastructure"] = "success"
            else:
                status["infrastructure"] = "empty"
        else:
            status["infrastructure"] = "not_executed"

        if results.api_interfaces:
            if "error" in results.api_interfaces:
                status["api_interfaces"] = "failed"
            elif any(results.api_interfaces.values()):
                status["api_interfaces"] = "success"
            else:
                status["api_interfaces"] = "empty"
        else:
            status["api_interfaces"] = "not_executed"

        return status

    def _identify_data_sources(self, results: ComponentDiscoveryResults) -> List[str]:
        """Identify what types of data sources were analyzed."""
        sources = []

        if results.infrastructure:
            if "deployment_topology" in results.infrastructure and results.infrastructure["deployment_topology"]:
                sources.append("deployment_topology")
            if "network_architecture" in results.infrastructure and results.infrastructure["network_architecture"]:
                sources.append("network_architecture")
            if "resource_dependencies" in results.infrastructure and results.infrastructure["resource_dependencies"]:
                sources.append("resource_dependencies")

        if results.api_interfaces:
            if "api_endpoints" in results.api_interfaces and results.api_interfaces["api_endpoints"]:
                sources.append("api_endpoints")
            if "service_contracts" in results.api_interfaces and results.api_interfaces["service_contracts"]:
                sources.append("service_contracts")
            if (
                "external_api_dependencies" in results.api_interfaces
                and results.api_interfaces["external_api_dependencies"]
            ):
                sources.append("external_api_dependencies")

        return sources

    def format_component_summary(self, results: ComponentDiscoveryResults) -> str:
        """Create a human-readable summary of discovered components."""
        lines = ["# Architecture Discovery Summary", ""]

        # Add infrastructure summary
        if results.infrastructure:
            lines.append("## Infrastructure Components")
            if "error" in results.infrastructure:
                lines.append(f"⚠️ Error: {results.infrastructure['error']}")
            else:
                infra_count = self._count_infrastructure_components(results.infrastructure)
                lines.append(f"Total infrastructure components: {infra_count}")

                if "deployment_topology" in results.infrastructure:
                    topology = results.infrastructure["deployment_topology"]
                    for comp_type, instances in topology.items():
                        if isinstance(instances, list):
                            lines.append(f"- {comp_type}: {len(instances)}")
                        elif isinstance(instances, dict):
                            lines.append(f"- {comp_type}: 1")
            lines.append("")

        # Add API summary
        if results.api_interfaces:
            lines.append("## API Components")
            if "error" in results.api_interfaces:
                lines.append(f"⚠️ Error: {results.api_interfaces['error']}")
            else:
                api_count = self._count_api_components(results.api_interfaces)
                lines.append(f"Total API components: {api_count}")

                for comp_type in ["api_endpoints", "service_contracts", "external_api_dependencies"]:
                    if comp_type in results.api_interfaces:
                        count = len(results.api_interfaces[comp_type])
                        if count > 0:
                            lines.append(f"- {comp_type}: {count}")
            lines.append("")

        # Add validation issues
        issues = self.validate_discovery_results(results)
        if issues:
            lines.append("## Validation Issues")
            for issue in issues:
                lines.append(f"⚠️ {issue}")
            lines.append("")

        return "\n".join(lines)
