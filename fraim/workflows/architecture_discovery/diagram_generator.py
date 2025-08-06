# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Diagram Generator

Handles generation of architecture diagrams in various formats
(Mermaid, PlantUML, Text) from component discovery results.
"""

from typing import Any, Dict, List
from fraim.config import Config
from .types import ComponentDiscoveryResults


class ArchitectureDiagramGenerator:
    """Generates architecture diagrams from component discovery results."""

    def __init__(self, config: Config):
        self.config = config

    async def generate_diagram(self, results: ComponentDiscoveryResults, format: str = "mermaid") -> str:
        """Generate architecture diagram in the specified format."""
        try:
            # Extract components from both discoveries
            infra_components = self._extract_infrastructure_components(results)
            api_components = self._extract_api_components(results)

            # Generate diagram based on format preference
            if format.lower() == "mermaid":
                diagram = self._generate_mermaid_diagram(
                    infra_components, api_components)
            elif format.lower() == "plantuml":
                diagram = self._generate_plantuml_diagram(
                    infra_components, api_components)
            else:
                diagram = self._generate_text_diagram(
                    infra_components, api_components)

            self.config.logger.info(f"Generated {format} architecture diagram")
            return diagram

        except Exception as e:
            self.config.logger.error(f"Diagram generation failed: {str(e)}")
            return f"Diagram generation failed: {str(e)}"

    def _extract_infrastructure_components(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Extract infrastructure components for diagram generation."""
        if not results.infrastructure:
            return []

        components = []

        # Add deployment topology components
        if "deployment_topology" in results.infrastructure:
            topology = results.infrastructure["deployment_topology"]

            # Add load balancers
            if "load_balancers" in topology:
                for lb in topology["load_balancers"]:
                    if isinstance(lb, dict):
                        components.append({
                            "name": lb.get("name", "Unknown LB"),
                            "type": "load_balancer",
                            "category": "infrastructure",
                            "external": lb.get("external", False),
                            "properties": lb
                        })

            # Add compute instances
            if "compute_instances" in topology:
                for instance in topology["compute_instances"]:
                    if isinstance(instance, dict):
                        components.append({
                            "name": instance.get("name", "Unknown Instance"),
                            "type": "compute_instance",
                            "category": "infrastructure",
                            "external": False,
                            "properties": instance
                        })

            # Add databases
            if "databases" in topology:
                for db in topology["databases"]:
                    if isinstance(db, dict):
                        components.append({
                            "name": db.get("name", "Unknown DB"),
                            "type": "database",
                            "category": "infrastructure",
                            "external": db.get("managed", False),
                            "properties": db
                        })

            # Add storage
            if "storage" in topology:
                for storage in topology["storage"]:
                    if isinstance(storage, dict):
                        components.append({
                            "name": storage.get("name", "Unknown Storage"),
                            "type": "storage",
                            "category": "infrastructure",
                            "external": storage.get("managed", False),
                            "properties": storage
                        })

        return components

    def _extract_api_components(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Extract API components for diagram generation."""
        if not results.api_interfaces:
            return []

        components = []

        # Add API endpoints as services
        if "api_endpoints" in results.api_interfaces:
            services: Dict[str, Dict[str, Any]] = {}
            endpoints = results.api_interfaces["api_endpoints"]

            # Group endpoints by service
            for endpoint in endpoints:
                if isinstance(endpoint, dict):
                    service_name = endpoint.get("service", "Unknown Service")
                    if service_name not in services:
                        services[service_name] = {
                            "endpoints": [],
                            "authentication": set(),
                            "protocols": set()
                        }

                    services[service_name]["endpoints"].append(endpoint)
                    services[service_name]["authentication"].add(
                        endpoint.get("authentication", "unknown"))
                    services[service_name]["protocols"].add(
                        endpoint.get("protocol", "HTTP"))

            # Create components for each service
            for service_name, service_data in services.items():
                components.append({
                    "name": service_name,
                    "type": "api_service",
                    "category": "api",
                    "external": False,
                    "properties": {
                        "endpoint_count": len(service_data["endpoints"]),
                        "authentication_methods": list(service_data["authentication"]),
                        "protocols": list(service_data["protocols"])
                    }
                })

        # Add external API dependencies
        if "external_api_dependencies" in results.api_interfaces:
            dependencies = results.api_interfaces["external_api_dependencies"]
            for dep in dependencies:
                if isinstance(dep, dict):
                    components.append({
                        "name": dep.get("name", "External API"),
                        "type": "external_api",
                        "category": "api",
                        "external": True,
                        "properties": dep
                    })

        return components

    def _generate_mermaid_diagram(self, infra_components: List[Dict], api_components: List[Dict]) -> str:
        """Generate Mermaid format architecture diagram."""
        lines = ["graph TD"]

        # Add infrastructure components
        for component in infra_components:
            node_id = self._sanitize_node_id(component["name"])
            node_type = component["type"]
            is_external = component.get("external", False)

            # Choose node shape based on type and external status
            if node_type == "load_balancer":
                if is_external:
                    lines.append(
                        f"    {node_id}{{{{'{component['name']}'}}}} style {node_id} fill:#ff9999")
                else:
                    lines.append(
                        f"    {node_id}[{component['name']}] style {node_id} fill:#99ccff")
            elif node_type == "database":
                if is_external:
                    lines.append(
                        f"    {node_id}[('{component['name']}')] style {node_id} fill:#ffcc99")
                else:
                    lines.append(
                        f"    {node_id}[('{component['name']}')] style {node_id} fill:#ccffcc")
            elif node_type == "storage":
                lines.append(
                    f"    {node_id}[/{component['name']}/] style {node_id} fill:#ffffcc")
            else:
                lines.append(
                    f"    {node_id}[{component['name']}] style {node_id} fill:#e6e6e6")

        # Add API components
        for component in api_components:
            node_id = self._sanitize_node_id(component["name"])
            is_external = component.get("external", False)

            if is_external:
                lines.append(
                    f"    {node_id}{{{{{component['name']}}}}} style {node_id} fill:#ffccff")
            else:
                lines.append(
                    f"    {node_id}{{{{{component['name']}}}}} style {node_id} fill:#ccffff")

        # Add connections based on component relationships
        connections = self._infer_connections(infra_components, api_components)
        for source, target, label in connections:
            source_id = self._sanitize_node_id(source)
            target_id = self._sanitize_node_id(target)
            if label:
                lines.append(f"    {source_id} -->|{label}| {target_id}")
            else:
                lines.append(f"    {source_id} --> {target_id}")

        # Add legend
        lines.append("")
        lines.append("    classDef external fill:#ff9999")
        lines.append("    classDef internal fill:#99ccff")
        lines.append("    classDef database fill:#ccffcc")
        lines.append("    classDef api fill:#ccffff")

        return "\n".join(lines)

    def _generate_plantuml_diagram(self, infra_components: List[Dict], api_components: List[Dict]) -> str:
        """Generate PlantUML format architecture diagram."""
        lines = ["@startuml", "!theme plain", ""]

        # Add infrastructure components
        for component in infra_components:
            node_id = self._sanitize_node_id(component["name"])
            node_type = component["type"]
            is_external = component.get("external", False)

            if node_type == "load_balancer":
                if is_external:
                    lines.append(f"cloud \"{component['name']}\" as {node_id}")
                else:
                    lines.append(
                        f"component \"{component['name']}\" as {node_id}")
            elif node_type == "database":
                lines.append(f"database \"{component['name']}\" as {node_id}")
            elif node_type == "storage":
                lines.append(f"storage \"{component['name']}\" as {node_id}")
            else:
                lines.append(f"rectangle \"{component['name']}\" as {node_id}")

        # Add API components
        for component in api_components:
            node_id = self._sanitize_node_id(component["name"])
            is_external = component.get("external", False)

            if is_external:
                lines.append(f"cloud \"{component['name']}\" as {node_id}")
            else:
                lines.append(f"interface \"{component['name']}\" as {node_id}")

        lines.append("")

        # Add connections
        connections = self._infer_connections(infra_components, api_components)
        for source, target, label in connections:
            source_id = self._sanitize_node_id(source)
            target_id = self._sanitize_node_id(target)
            if label:
                lines.append(f"{source_id} --> {target_id} : {label}")
            else:
                lines.append(f"{source_id} --> {target_id}")

        lines.append("@enduml")
        return "\n".join(lines)

    def _generate_text_diagram(self, infra_components: List[Dict], api_components: List[Dict]) -> str:
        """Generate text-based architecture diagram."""
        lines = ["# System Architecture", ""]

        if infra_components:
            lines.append("## Infrastructure Components:")
            lines.append("")

            # Group by type
            component_types: Dict[str, List[Dict[str, Any]]] = {}
            for component in infra_components:
                comp_type = component["type"]
                if comp_type not in component_types:
                    component_types[comp_type] = []
                component_types[comp_type].append(component)

            for comp_type, components in component_types.items():
                lines.append(f"### {comp_type.title().replace('_', ' ')}:")
                for component in components:
                    external_marker = " (External)" if component.get(
                        "external") else ""
                    lines.append(f"- {component['name']}{external_marker}")

                    # Add properties if available
                    props = component.get("properties", {})
                    if props:
                        for key, value in props.items():
                            if key not in ["name", "type"] and value:
                                lines.append(f"  - {key}: {value}")
                lines.append("")

        if api_components:
            lines.append("## API Components:")
            lines.append("")

            for component in api_components:
                external_marker = " (External)" if component.get(
                    "external") else ""
                lines.append(f"- {component['name']}{external_marker}")

                # Add properties
                props = component.get("properties", {})
                if props:
                    for key, value in props.items():
                        if value:
                            lines.append(f"  - {key}: {value}")
            lines.append("")

        # Add data flows if available
        connections = self._infer_connections(infra_components, api_components)
        if connections:
            lines.append("## Component Relationships:")
            lines.append("")
            for source, target, label in connections:
                if label:
                    lines.append(f"- {source} → {target} ({label})")
                else:
                    lines.append(f"- {source} → {target}")

        return "\n".join(lines)

    def _sanitize_node_id(self, name: str) -> str:
        """Sanitize node name for diagram generation."""
        return "".join(c for c in name if c.isalnum() or c in "_")[:20]

    def _infer_connections(self, infra_components: List[Dict], api_components: List[Dict]) -> List[tuple]:
        """Infer connections between components based on common patterns."""
        connections = []

        # Find load balancers and connect to compute instances
        load_balancers = [
            c for c in infra_components if c["type"] == "load_balancer"]
        compute_instances = [
            c for c in infra_components if c["type"] == "compute_instance"]

        for lb in load_balancers:
            for instance in compute_instances:
                # Simple heuristic: external LBs connect to instances
                if lb.get("external", False):
                    connections.append(
                        (lb["name"], instance["name"], "HTTP/HTTPS"))

        # Connect compute instances to databases
        databases = [c for c in infra_components if c["type"] == "database"]
        for instance in compute_instances:
            for db in databases:
                connections.append((instance["name"], db["name"], "SQL"))

        # Connect compute instances to storage
        storage_components = [
            c for c in infra_components if c["type"] == "storage"]
        for instance in compute_instances:
            for storage in storage_components:
                connections.append((instance["name"], storage["name"], "API"))

        # Connect API services to compute instances (simplified)
        api_services = [c for c in api_components if c["type"]
                        == "api_service" and not c.get("external")]
        for api in api_services:
            if compute_instances:
                # Connect to first compute instance as example
                connections.append(
                    (api["name"], compute_instances[0]["name"], "Internal API"))

        # Connect to external APIs
        external_apis = [c for c in api_components if c.get("external", False)]
        for ext_api in external_apis:
            if compute_instances:
                connections.append(
                    (compute_instances[0]["name"], ext_api["name"], "External API"))

        return connections
