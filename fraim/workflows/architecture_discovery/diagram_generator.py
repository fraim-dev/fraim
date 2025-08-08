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

            # Diagnostic logging for empty diagrams
            total_components = len(infra_components) + len(api_components)
            self.config.logger.info(
                f"Extracted {len(infra_components)} infrastructure components and {len(api_components)} API components"
            )

            if total_components == 0:
                self.config.logger.warning("No components found for diagram generation")
                self._log_diagnostic_info(results)
                return (
                    'graph TD\n    Empty["No components discovered"]\n    '
                    "style Empty fill:#ffcccc\n    "
                    'Empty --> Note["Check logs for component discovery errors"]'
                )

            # Generate diagram based on format preference
            if format.lower() == "mermaid":
                diagram = self._generate_mermaid_diagram(infra_components, api_components)
            elif format.lower() == "plantuml":
                diagram = self._generate_plantuml_diagram(infra_components, api_components)
            else:
                diagram = self._generate_text_diagram(infra_components, api_components)

            self.config.logger.info(f"Generated {format} architecture diagram")
            return diagram

        except Exception as e:
            self.config.logger.error(f"Diagram generation failed: {str(e)}")
            return f"Diagram generation failed: {str(e)}"

    def _log_diagnostic_info(self, results: ComponentDiscoveryResults) -> None:
        """Log diagnostic information to help users debug empty diagrams."""
        self.config.logger.info("=== ARCHITECTURE DIAGRAM DIAGNOSTIC INFO ===")

        # Check infrastructure results
        if results.infrastructure is None:
            self.config.logger.warning("Infrastructure discovery results are None")
        elif isinstance(results.infrastructure, dict):
            if "error" in results.infrastructure:
                self.config.logger.error(f"Infrastructure discovery error: {results.infrastructure['error']}")
            else:
                self.config.logger.info(f"Infrastructure keys: {list(results.infrastructure.keys())}")

                # Check for actual infrastructure keys
                for key in ["infrastructure_components", "container_configs", "deployment_environments"]:
                    if key in results.infrastructure:
                        value = results.infrastructure[key]
                        if isinstance(value, list):
                            self.config.logger.info(f"Found {len(value)} items in {key}")
                        else:
                            self.config.logger.info(f"{key} is not a list: {type(value)}")
                    else:
                        self.config.logger.warning(f"{key} not found in infrastructure results")

                # Legacy check for deployment_topology
                if "deployment_topology" in results.infrastructure:
                    topology = results.infrastructure["deployment_topology"]
                    if isinstance(topology, dict) and len(topology) == 0:
                        self.config.logger.warning("deployment_topology is empty - no infrastructure components found")
                    else:
                        self.config.logger.info(
                            f"deployment_topology keys: {list(topology.keys()) if isinstance(topology, dict) else 'not a dict'}"
                        )

        # Check API results
        if results.api_interfaces is None:
            self.config.logger.warning("API interface discovery results are None")
        elif isinstance(results.api_interfaces, dict):
            if "error" in results.api_interfaces:
                self.config.logger.error(f"API interface discovery error: {results.api_interfaces['error']}")
            else:
                self.config.logger.info(f"API interface keys: {list(results.api_interfaces.keys())}")

                # Check for actual API keys
                for key in ["rest_endpoints", "graphql_schema", "websocket_connections", "data_models"]:
                    if key in results.api_interfaces:
                        value = results.api_interfaces[key]
                        if isinstance(value, list):
                            self.config.logger.info(f"Found {len(value)} items in {key}")
                        else:
                            self.config.logger.info(f"{key} is not a list: {type(value)}")
                    else:
                        self.config.logger.warning(f"{key} not found in API interface results")

                # Legacy check for api_endpoints
                if "api_endpoints" in results.api_interfaces:
                    endpoints = results.api_interfaces["api_endpoints"]
                    if isinstance(endpoints, list) and len(endpoints) == 0:
                        self.config.logger.warning("api_endpoints is empty - no API components found")
                    else:
                        self.config.logger.info(f"Found {len(endpoints)} API endpoints")

        self.config.logger.info("=== END DIAGNOSTIC INFO ===")

    def _extract_infrastructure_components(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Extract infrastructure components for diagram generation."""
        if not results.infrastructure:
            return []

        components = []

        # Handle the actual structure returned by infrastructure discovery
        if "infrastructure_components" in results.infrastructure:
            infra_components = results.infrastructure["infrastructure_components"]
            for component in infra_components:
                if isinstance(component, dict):
                    components.append(
                        {
                            "name": component.get("name", "Unknown Component"),
                            "type": component.get("type", "infrastructure"),
                            "category": "infrastructure",
                            "external": component.get("external", False),
                            "properties": component,
                        }
                    )

        # Handle container configurations as compute instances
        if "container_configs" in results.infrastructure:
            containers = results.infrastructure["container_configs"]
            for container in containers:
                if isinstance(container, dict):
                    components.append(
                        {
                            "name": container.get("name", container.get("image", "Unknown Container")),
                            "type": "compute_instance",
                            "category": "infrastructure",
                            "external": False,
                            "properties": container,
                        }
                    )

        # Handle deployment environments
        if "deployment_environments" in results.infrastructure:
            environments = results.infrastructure["deployment_environments"]
            for env in environments:
                if isinstance(env, dict):
                    components.append(
                        {
                            "name": env.get("name", "Unknown Environment"),
                            "type": "environment",
                            "category": "infrastructure",
                            "external": env.get("external", False),
                            "properties": env,
                        }
                    )

        # Legacy support: Handle the expected deployment_topology structure
        if "deployment_topology" in results.infrastructure:
            topology = results.infrastructure["deployment_topology"]

            # Add load balancers
            if "load_balancers" in topology:
                for lb in topology["load_balancers"]:
                    if isinstance(lb, dict):
                        components.append(
                            {
                                "name": lb.get("name", "Unknown LB"),
                                "type": "load_balancer",
                                "category": "infrastructure",
                                "external": lb.get("external", False),
                                "properties": lb,
                            }
                        )

            # Add compute instances
            if "compute_instances" in topology:
                for instance in topology["compute_instances"]:
                    if isinstance(instance, dict):
                        components.append(
                            {
                                "name": instance.get("name", "Unknown Instance"),
                                "type": "compute_instance",
                                "category": "infrastructure",
                                "external": False,
                                "properties": instance,
                            }
                        )

            # Add databases
            if "databases" in topology:
                for db in topology["databases"]:
                    if isinstance(db, dict):
                        components.append(
                            {
                                "name": db.get("name", "Unknown DB"),
                                "type": "database",
                                "category": "infrastructure",
                                "external": db.get("managed", False),
                                "properties": db,
                            }
                        )

            # Add storage
            if "storage" in topology:
                for storage in topology["storage"]:
                    if isinstance(storage, dict):
                        components.append(
                            {
                                "name": storage.get("name", "Unknown Storage"),
                                "type": "storage",
                                "category": "infrastructure",
                                "external": storage.get("managed", False),
                                "properties": storage,
                            }
                        )

        return components

    def _extract_api_components(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Extract API components for diagram generation."""
        if not results.api_interfaces:
            return []

        components = []

        # Handle the actual structure returned by API interface discovery

        # Handle REST endpoints
        if "rest_endpoints" in results.api_interfaces:
            rest_endpoints = results.api_interfaces["rest_endpoints"]
            services: Dict[str, Dict[str, Any]] = {}

            # Group REST endpoints by service
            for endpoint in rest_endpoints:
                if isinstance(endpoint, dict):
                    service_name = endpoint.get(
                        "service",
                        endpoint.get("path", "REST API").split("/")[1] if endpoint.get("path") else "REST API",
                    )
                    if service_name not in services:
                        services[service_name] = {"endpoints": [], "methods": set(), "paths": set()}

                    services[service_name]["endpoints"].append(endpoint)
                    services[service_name]["methods"].add(endpoint.get("method", "GET"))
                    services[service_name]["paths"].add(endpoint.get("path", "/"))

            # Create components for each REST service
            for service_name, service_data in services.items():
                components.append(
                    {
                        "name": f"{service_name} API",
                        "type": "api_service",
                        "category": "api",
                        "external": False,
                        "properties": {
                            "endpoint_count": len(service_data["endpoints"]),
                            "methods": list(service_data["methods"]),
                            "paths": list(service_data["paths"]),
                            "type": "REST",
                        },
                    }
                )

        # Handle GraphQL schemas
        if "graphql_schema" in results.api_interfaces:
            graphql_schemas = results.api_interfaces["graphql_schema"]
            if graphql_schemas:
                components.append(
                    {
                        "name": "GraphQL API",
                        "type": "api_service",
                        "category": "api",
                        "external": False,
                        "properties": {"schema_count": len(graphql_schemas), "type": "GraphQL"},
                    }
                )

        # Handle WebSocket connections
        if "websocket_connections" in results.api_interfaces:
            websockets = results.api_interfaces["websocket_connections"]
            if websockets:
                components.append(
                    {
                        "name": "WebSocket API",
                        "type": "api_service",
                        "category": "api",
                        "external": False,
                        "properties": {"connection_count": len(websockets), "type": "WebSocket"},
                    }
                )

        # Legacy support: Handle the expected api_endpoints structure
        if "api_endpoints" in results.api_interfaces:
            legacy_services: Dict[str, Dict[str, Any]] = {}
            endpoints = results.api_interfaces["api_endpoints"]

            # Group endpoints by service
            for endpoint in endpoints:
                if isinstance(endpoint, dict):
                    service_name = endpoint.get("service", "Unknown Service")
                    if service_name not in legacy_services:
                        legacy_services[service_name] = {"endpoints": [], "authentication": set(), "protocols": set()}

                    legacy_services[service_name]["endpoints"].append(endpoint)
                    legacy_services[service_name]["authentication"].add(endpoint.get("authentication", "unknown"))
                    legacy_services[service_name]["protocols"].add(endpoint.get("protocol", "HTTP"))

            # Create components for each service
            for service_name, service_data in legacy_services.items():
                components.append(
                    {
                        "name": service_name,
                        "type": "api_service",
                        "category": "api",
                        "external": False,
                        "properties": {
                            "endpoint_count": len(service_data["endpoints"]),
                            "authentication_methods": list(service_data["authentication"]),
                            "protocols": list(service_data["protocols"]),
                        },
                    }
                )

        # Handle external API dependencies (if present)
        if "external_api_dependencies" in results.api_interfaces:
            dependencies = results.api_interfaces["external_api_dependencies"]
            for dep in dependencies:
                if isinstance(dep, dict):
                    components.append(
                        {
                            "name": dep.get("name", "External API"),
                            "type": "external_api",
                            "category": "api",
                            "external": True,
                            "properties": dep,
                        }
                    )

        return components

    def _generate_mermaid_diagram(self, infra_components: List[Dict], api_components: List[Dict]) -> str:
        """Generate Mermaid format architecture diagram."""
        lines = ["graph TD"]

        # Track nodes to avoid duplicates
        defined_nodes = set()
        node_styles = []

        # Add infrastructure components
        for component in infra_components:
            node_id = self._sanitize_node_id(component["name"])
            node_type = component["type"]
            is_external = component.get("external", False)

            # Skip if already defined
            if node_id in defined_nodes:
                continue
            defined_nodes.add(node_id)

            # Choose node shape based on type
            if node_type == "load_balancer":
                if is_external:
                    lines.append(f"    {node_id}{{{{{component['name']}}}}}")
                else:
                    lines.append(f"    {node_id}[{component['name']}]")
            elif node_type == "database":
                lines.append(f"    {node_id}[('{component['name']}')]")
            elif node_type == "storage":
                lines.append(f"    {node_id}[/{component['name']}/]")
            else:
                lines.append(f"    {node_id}[{component['name']}]")

            # Store style information for later application
            if node_type == "database":
                if is_external:
                    node_styles.append(f"    style {node_id} fill:#ffcc99,color:#000000")
                else:
                    node_styles.append(f"    style {node_id} fill:#ccffcc,color:#000000")
            elif is_external:
                node_styles.append(f"    style {node_id} fill:#ff9999,color:#000000")
            else:
                node_styles.append(f"    style {node_id} fill:#e6e6e6,color:#000000")

        # Add API components
        for component in api_components:
            node_id = self._sanitize_node_id(component["name"])
            is_external = component.get("external", False)

            # Skip if already defined
            if node_id in defined_nodes:
                continue
            defined_nodes.add(node_id)

            lines.append(f"    {node_id}{{{{{component['name']}}}}}")

            # Store style information
            if is_external:
                node_styles.append(f"    style {node_id} fill:#ffccff,color:#000000")
            else:
                node_styles.append(f"    style {node_id} fill:#ccffff,color:#000000")

        # Add connections based on component relationships
        connections = self._infer_connections(infra_components, api_components)
        if connections:
            lines.append("")
        for source, target, label in connections:
            source_id = self._sanitize_node_id(source)
            target_id = self._sanitize_node_id(target)
            if label:
                lines.append(f"    {source_id} -->|{label}| {target_id}")
            else:
                lines.append(f"    {source_id} --> {target_id}")

        # Apply styles
        if node_styles:
            lines.append("")
            lines.append("    %% Apply styles")
            lines.extend(node_styles)

        # Add class definitions
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
                    lines.append(f'cloud "{component["name"]}" as {node_id}')
                else:
                    lines.append(f'component "{component["name"]}" as {node_id}')
            elif node_type == "database":
                lines.append(f'database "{component["name"]}" as {node_id}')
            elif node_type == "storage":
                lines.append(f'storage "{component["name"]}" as {node_id}')
            else:
                lines.append(f'rectangle "{component["name"]}" as {node_id}')

        # Add API components
        for component in api_components:
            node_id = self._sanitize_node_id(component["name"])
            is_external = component.get("external", False)

            if is_external:
                lines.append(f'cloud "{component["name"]}" as {node_id}')
            else:
                lines.append(f'interface "{component["name"]}" as {node_id}')

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
                    external_marker = " (External)" if component.get("external") else ""
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
                external_marker = " (External)" if component.get("external") else ""
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
        load_balancers = [c for c in infra_components if c["type"] == "load_balancer"]
        compute_instances = [c for c in infra_components if c["type"] == "compute_instance"]

        for lb in load_balancers:
            for instance in compute_instances:
                # Simple heuristic: external LBs connect to instances
                if lb.get("external", False):
                    connections.append((lb["name"], instance["name"], "HTTP/HTTPS"))

        # Connect compute instances to databases
        databases = [c for c in infra_components if c["type"] == "database"]
        for instance in compute_instances:
            for db in databases:
                connections.append((instance["name"], db["name"], "SQL"))

        # Connect compute instances to storage
        storage_components = [c for c in infra_components if c["type"] == "storage"]
        for instance in compute_instances:
            for storage in storage_components:
                connections.append((instance["name"], storage["name"], "API"))

        # Connect API services to compute instances (simplified)
        api_services = [c for c in api_components if c["type"] == "api_service" and not c.get("external")]
        for api in api_services:
            if compute_instances:
                # Connect to first compute instance as example
                connections.append((api["name"], compute_instances[0]["name"], "Internal API"))

        # Connect to external APIs
        external_apis = [c for c in api_components if c.get("external", False)]
        for ext_api in external_apis:
            if compute_instances:
                connections.append((compute_instances[0]["name"], ext_api["name"], "External API"))

        return connections
