# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Diagram Generator

Handles generation of architecture diagrams in Mermaid format from component
discovery results. The architecture is designed to be extensible for future
diagram formats.
"""

from typing import Any, Dict, List, Tuple

from fraim.config import Config

from .types import ComponentDiscoveryResults


class ArchitectureDiagramGenerator:
    """Generates architecture diagrams from component discovery results.

    Currently supports Mermaid format. The architecture is designed to be
    extensible - future formats can be added by:
    1. Adding a format parameter to generate_diagram()
    2. Adding format-specific generation methods (e.g., _generate_plantuml_diagram)
    3. Adding conditional logic in generate_diagram() to call the appropriate method
    """

    def __init__(self, config: Config):
        self.config = config

    async def generate_diagram(self, results: ComponentDiscoveryResults) -> str:
        """Generate architecture diagram in Mermaid format."""
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

            # Generate Mermaid diagram with discovered relationships
            diagram = self._generate_mermaid_diagram(
                infra_components, api_components, results)

            self.config.logger.info("Generated Mermaid architecture diagram")
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

                # Check for actual infrastructure keys (deployment_environments excluded as they're in separate file)
                for key in ["infrastructure_components", "container_configs"]:
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

        # Note: Deployment environments are now handled separately in deployment_environments.json
        # and are not included in the architecture diagram as they represent operational
        # deployment contexts rather than architectural components

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
        components = []

        # First, extract API components from unified components if available
        if results.unified_components and results.unified_components.components:
            for unified_comp in results.unified_components.components:
                # Add API service components from unified components
                if (unified_comp.component_type == "service" and
                        unified_comp.api_interfaces and len(unified_comp.api_interfaces) > 0):
                    components.append({
                        "name": unified_comp.component_name,
                        "type": "api_service",
                        "category": "api",
                        "external": False,
                        "properties": {
                            "api_interfaces": unified_comp.api_interfaces,
                            "endpoints": unified_comp.endpoints or [],
                            "protocols": unified_comp.protocols or []
                        }
                    })

        # Fallback to legacy API interface extraction if no unified components
        if not components and results.api_interfaces:
            # Handle REST endpoints - Create individual API service components instead of generic ones
            if "rest_endpoints" in results.api_interfaces:
                rest_endpoints = results.api_interfaces["rest_endpoints"]
                services: Dict[str, Dict[str, Any]] = {}

                # Group REST endpoints by service
                for endpoint in rest_endpoints:
                    if isinstance(endpoint, dict):
                        service_name = endpoint.get(
                            "service",
                            endpoint.get("path", "REST API").split(
                                "/")[1] if endpoint.get("path") else "REST API",
                        )
                        if service_name not in services:
                            services[service_name] = {
                                "endpoints": [], "methods": set(), "paths": set()}

                        services[service_name]["endpoints"].append(endpoint)
                        services[service_name]["methods"].add(
                            endpoint.get("method", "GET"))
                        services[service_name]["paths"].add(
                            endpoint.get("path", "/"))

                # Create components for each REST service with proper naming for flow matching
                for service_name, service_data in services.items():
                    # Create individual API service components that match data flow naming
                    api_component_name = f"{service_name.replace('_', '-')} API Service" if service_name != "REST API" else "REST API API"
                    components.append(
                        {
                            "name": api_component_name,
                            "type": "api_service",
                            "category": "api",
                            "external": False,
                            "properties": {
                                "endpoint_count": len(service_data["endpoints"]),
                                "methods": list(service_data["methods"]),
                                "paths": list(service_data["paths"]),
                                "type": "REST",
                                "service_identifier": service_name  # For matching with data flows
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

    def _generate_mermaid_diagram(self, infra_components: List[Dict], api_components: List[Dict], results: ComponentDiscoveryResults) -> str:
        """Generate Mermaid format architecture diagram."""
        lines = ["graph TD"]

        # Track nodes to avoid duplicates
        defined_nodes: set[str] = set()
        node_styles: List[str] = []

        # Group components by type for better organization
        infra_by_type: Dict[str, List[Dict[str, Any]]] = {}
        for component in infra_components:
            comp_type = component["type"]
            if comp_type not in infra_by_type:
                infra_by_type[comp_type] = []
            infra_by_type[comp_type].append(component)

        api_by_type: Dict[str, List[Dict[str, Any]]] = {}
        for component in api_components:
            comp_type = component["type"]
            if comp_type not in api_by_type:
                api_by_type[comp_type] = []
            api_by_type[comp_type].append(component)

        # Add infrastructure components with organized sections
        if infra_components:
            lines.append("")
            lines.append("    %% Infrastructure Components")

        # Define order for infrastructure component types for better layout
        infra_type_order = ["storage", "database",
                            "compute_instance", "load_balancer", "environment"]

        for comp_type in infra_type_order:
            if comp_type in infra_by_type:
                components = infra_by_type[comp_type]
                if components:
                    type_name = comp_type.replace("_", " ").title()
                    lines.append(f"    %% {type_name} Services")
                self._add_infrastructure_nodes(
                    lines, components, defined_nodes, node_styles)
                del infra_by_type[comp_type]

        # Add any remaining infrastructure components not in the standard order
        for comp_type, components in infra_by_type.items():
            if components:
                type_name = comp_type.replace("_", " ").title()
                lines.append(f"    %% {type_name} Services")
            self._add_infrastructure_nodes(
                lines, components, defined_nodes, node_styles)

        # Add API components with organized sections
        if api_components:
            lines.append("")
            lines.append("    %% API Services")

        for comp_type, components in api_by_type.items():
            if components:
                type_name = comp_type.replace("_", " ").title()
                lines.append(f"    %% {type_name}s")
            self._add_api_nodes(lines, components, defined_nodes, node_styles)

        # Add connections based on discovered relationships and data flows
        connections = self._extract_discovered_connections(
            results, infra_components, api_components)
        if connections:
            lines.append("")
            lines.append("    %% Component Connections")
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

    def _add_infrastructure_nodes(self, lines: List[str], components: List[Dict], defined_nodes: set[str], node_styles: List[str]) -> None:
        """Add infrastructure component nodes to the diagram."""
        for component in components:
            node_id = self._sanitize_node_id(component["name"])
            node_type = component["type"]
            is_external = component.get("external", False)

            # Skip if already defined
            if node_id in defined_nodes:
                continue
            defined_nodes.add(node_id)

            # Choose node shape based on type
            sanitized_label = self._sanitize_node_label(component['name'])
            if node_type == "load_balancer":
                if is_external:
                    lines.append(f"    {node_id}{{{{{sanitized_label}}}}}")
                else:
                    lines.append(f"    {node_id}[{sanitized_label}]")
            elif node_type == "database":
                lines.append(f"    {node_id}[({sanitized_label})]")
            elif node_type == "storage":
                lines.append(f"    {node_id}[/{sanitized_label}/]")
            else:
                lines.append(f"    {node_id}[{sanitized_label}]")

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

    def _add_api_nodes(self, lines: List[str], components: List[Dict], defined_nodes: set[str], node_styles: List[str]) -> None:
        """Add API component nodes to the diagram."""
        for component in components:
            node_id = self._sanitize_node_id(component["name"])
            is_external = component.get("external", False)

            # Skip if already defined
            if node_id in defined_nodes:
                continue
            defined_nodes.add(node_id)

            sanitized_label = self._sanitize_node_label(component['name'])
            lines.append(f"    {node_id}{{{{{sanitized_label}}}}}")

            # Store style information
            if is_external:
                node_styles.append(f"    style {node_id} fill:#ffccff,color:#000000")
            else:
                node_styles.append(f"    style {node_id} fill:#ccffff,color:#000000")

    def _sanitize_node_id(self, name: str) -> str:
        """Sanitize node name for diagram generation."""
        return "".join(c for c in name if c.isalnum() or c in "_")[:20]

    def _sanitize_node_label(self, name: str) -> str:
        """Sanitize node label to avoid Mermaid syntax conflicts.
        
        Removes or replaces characters that can cause parsing issues in Mermaid,
        particularly parentheses within square bracket node definitions.
        """
        # Replace parentheses with spaces or alternative formatting
        sanitized = name.replace("(", "").replace(")", "")
        # Clean up multiple spaces
        sanitized = " ".join(sanitized.split())
        return sanitized

    def _infer_connections(self, infra_components: List[Dict], api_components: List[Dict]) -> List[tuple]:
        """Infer connections between components based on common patterns."""
        connections = []
        seen_connections = set()  # Track connections to prevent duplicates

        # Helper function to add unique connections
        def add_connection(source: str, target: str, label: str = "") -> None:
            connection_key = (source, target, label)
            if connection_key not in seen_connections:
                seen_connections.add(connection_key)
                connections.append(connection_key)

        # Find load balancers and connect to compute instances
        load_balancers = [c for c in infra_components if c["type"] == "load_balancer"]
        compute_instances = [c for c in infra_components if c["type"] == "compute_instance"]

        for lb in load_balancers:
            for instance in compute_instances:
                # Simple heuristic: external LBs connect to instances
                if lb.get("external", False):
                    add_connection(lb["name"], instance["name"], "HTTP/HTTPS")

        # Connect compute instances to databases (limit to avoid overload)
        databases = [c for c in infra_components if c["type"] == "database"]
        for instance in compute_instances:
            # Limit to first 3 databases to avoid diagram overload
            for db in databases[:3]:
                add_connection(instance["name"], db["name"], "SQL")

        # Connect compute instances to storage (limit to avoid overload)
        storage_components = [c for c in infra_components if c["type"] == "storage"]
        for instance in compute_instances:
            # Limit to first 3 storage components
            for storage in storage_components[:3]:
                add_connection(instance["name"],
                               storage["name"], "Storage API")

        # Connect API services to compute instances (simplified)
        api_services = [c for c in api_components if c["type"] == "api_service" and not c.get("external")]
        for api in api_services:
            if compute_instances:
                # Connect to first compute instance as example
                add_connection(api["name"], compute_instances[0]
                               ["name"], "Internal API")

        # Connect to external APIs
        external_apis = [c for c in api_components if c.get("external", False)]
        for ext_api in external_apis:
            if compute_instances:
                add_connection(
                    compute_instances[0]["name"], ext_api["name"], "External API")

        return connections

    def _extract_discovered_connections(self, results: ComponentDiscoveryResults, infra_components: List[Dict], api_components: List[Dict]) -> List[tuple]:
        """Extract connections from discovered data flows and relationships."""
        connections = []
        seen_connections = set()  # Track connections to prevent duplicates

        # Helper function to add unique connections
        def add_connection(source: str, target: str, label: str = "") -> None:
            connection_key = (source, target, label)
            if connection_key not in seen_connections:
                seen_connections.add(connection_key)
                connections.append(connection_key)

        # Create a mapping of component IDs to display names for the diagram
        component_id_to_name = {}

        # Map from unified components if available
        if results.unified_components and results.unified_components.components:
            for comp in results.unified_components.components:
                component_id_to_name[comp.component_id] = comp.component_name

        # Also create reverse mapping from names to find components
        all_component_names = set()
        for comp_dict in infra_components + api_components:
            all_component_names.add(comp_dict["name"])

        # 1. Use data flows to create connections (primary source)
        if results.data_flows:
            self.config.logger.info(
                f"Processing {len(results.data_flows)} data flows for diagram connections")
            self.config.logger.info(
                f"Available component names in diagram: {sorted(list(all_component_names))[:10]}...")

            # Analyze missing components in data flows
            self._analyze_missing_components(
                results.data_flows, all_component_names)

            # Group and filter data flows to avoid diagram overload
            connection_counts: Dict[Tuple[str, str], int] = {}
            for flow in results.data_flows:
                source = flow.get("source", "")
                target = flow.get("target", "")

                # Skip external connections for cleaner diagram
                # But keep service-to-service and service-to-infra connections
                if (source == "external" and target == "external") or \
                   (source == "external" and not target.startswith(("service_", "infra_", "api_"))) or \
                   (target == "external" and not source.startswith(("service_", "infra_", "api_"))):
                    continue

                # Debug: Log the first few connections we're trying to process
                if len(connection_counts) < 5:
                    self.config.logger.info(
                        f"Processing flow: {source} -> {target}")

                # Special debug for API flows
                if "api" in source.lower() or "api" in target.lower():
                    if len(connection_counts) < 10:  # Log more API flows for debugging
                        self.config.logger.info(
                            f"API flow detected: {source} -> {target}")

                # Map component IDs to display names
                source_name = component_id_to_name.get(source, source)
                target_name = component_id_to_name.get(target, target)

                # Clean up component names for display
                source_name = self._clean_component_name(source_name)
                target_name = self._clean_component_name(target_name)

                # Skip if we don't have both components in our diagram
                # Also check for close matches (with different cases/formats)
                source_matches = self._find_component_match(
                    source_name, all_component_names)
                target_matches = self._find_component_match(
                    target_name, all_component_names)

                if not source_matches or not target_matches:
                    # Enhanced debug logging for match failures
                    if len(connection_counts) < 10:  # Debug more failures
                        missing_component = "source" if not source_matches else "target"
                        missing_name = source_name if not source_matches else target_name
                        self.config.logger.info(
                            f"No {missing_component} match: {source_name} -> {target_name} (from {source} -> {target})")
                        self.config.logger.info(
                            f"  Missing component: '{missing_name}' not found in {len(all_component_names)} available components")

                        # Show a few available components for reference
                        sample_components = list(all_component_names)[:5]
                        self.config.logger.info(
                            f"  Available components (sample): {sample_components}")

                    # Special debug for API matching failures
                    if "api" in source.lower() or "api" in target.lower():
                        self.config.logger.debug(
                            f"API match failure: {source_name} -> {target_name} (from {source} -> {target})")
                        self.config.logger.debug(
                            f"  Source match attempted: '{source_name}' -> Found: {bool(source_matches)}")
                        self.config.logger.debug(
                            f"  Target match attempted: '{target_name}' -> Found: {bool(target_matches)}")
                    continue

                # Use the matched names from the diagram
                source_name = source_matches
                target_name = target_matches

                # Count connections to limit diagram complexity
                conn_key = (source_name, target_name)
                connection_counts[conn_key] = connection_counts.get(
                    conn_key, 0) + 1

            # Use category-based connection limits to ensure important connection types are visible
            categorized_connections = self._categorize_connections_by_type(
                connection_counts, results.data_flows)

            # Define limits per category to ensure balanced representation
            category_limits = {
                "database": 25,        # Database connections (high priority)
                "api": 30,            # API connections
                "infrastructure": 20,  # Infrastructure connections
                "service": 25,        # Service-to-service connections
                "other": 15           # Other connection types
            }

            # Add connections from each category up to its limit
            for category, category_connections in categorized_connections.items():
                limit = category_limits.get(category, 10)
                sorted_category_connections = sorted(
                    category_connections, key=lambda x: x[1], reverse=True)

                for connection_info in sorted_category_connections[:limit]:
                    (source_name, target_name), count = connection_info
                    # Determine connection label based on the flows
                    label = self._determine_connection_label(
                        results.data_flows, source_name, target_name)
                    add_connection(source_name, target_name, label)

        # 2. Use component relationships as fallback/additional connections
        elif results.unified_components and results.unified_components.component_relationships:
            self.config.logger.info(
                f"Processing {len(results.unified_components.component_relationships)} component relationships")

            for relationship in results.unified_components.component_relationships:
                source_id = relationship.get("source", "")
                target_id = relationship.get("target", "")
                rel_type = relationship.get("type", "")

                # Map to display names
                source_name = component_id_to_name.get(source_id, source_id)
                target_name = component_id_to_name.get(target_id, target_id)

                # Clean names
                source_name = self._clean_component_name(source_name)
                target_name = self._clean_component_name(target_name)

                # Skip if we don't have both components
                if source_name not in all_component_names or target_name not in all_component_names:
                    continue

                # Create label from relationship type
                label = self._relationship_type_to_label(rel_type)
                add_connection(source_name, target_name, label)

        # 3. Fallback to old inference method if no discovered relationships
        else:
            self.config.logger.warning(
                "No data flows or relationships found, using basic connection inference")
            return self._infer_connections(infra_components, api_components)

        self.config.logger.info(
            f"Created {len(connections)} connections for diagram")
        return connections

    def _clean_component_name(self, name: str) -> str:
        """Clean component name for diagram display with enhanced normalization."""
        if not name:
            return ""

        original_name = name

        # Remove common prefixes that make names too long
        prefixes_to_remove = ["service_", "infra_", "api_", "app_", "web_"]
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break  # Only remove first matching prefix

        # Normalize separators consistently
        name = name.replace("_", "-").replace(" ", "-")

        # Remove duplicate hyphens
        while "--" in name:
            name = name.replace("--", "-")

        # Strip leading/trailing hyphens
        name = name.strip("-")

        # Log transformation for debugging
        if name != original_name:
            self.config.logger.debug(
                f"Name cleaning: '{original_name}' → '{name}'")

        return name

    def _determine_connection_label(self, data_flows: List[Dict], source_name: str, target_name: str) -> str:
        """Determine the best label for a connection based on data flows."""
        # Find flows between these components
        relevant_flows = []
        for flow in data_flows:
            flow_source = self._clean_component_name(flow.get("source", ""))
            flow_target = self._clean_component_name(flow.get("target", ""))

            if flow_source == source_name and flow_target == target_name:
                relevant_flows.append(flow)

        if not relevant_flows:
            return ""

        # Determine the most common/important protocol or type
        protocols = []
        flow_types = []

        for flow in relevant_flows:
            if flow.get("protocol"):
                protocols.append(flow["protocol"])
            if flow.get("type"):
                flow_types.append(flow["type"])

        # Choose the best label
        if protocols:
            # Simplified - just use first protocol
            most_common_protocol = protocols[0]
            for protocol in protocols:
                if protocols.count(protocol) > protocols.count(most_common_protocol):
                    most_common_protocol = protocol

            if str(most_common_protocol).lower() in ["postgresql", "mysql", "mongodb", "redis"]:
                return "Database"
            elif str(most_common_protocol).lower() in ["http", "https"]:
                return "API"
            elif str(most_common_protocol).lower() in ["kafka", "amqp", "sqs"]:
                return "Queue"
            else:
                return str(most_common_protocol).upper()

        if flow_types:
            # Simplified - just use first type
            most_common_type = flow_types[0]
            for flow_type in flow_types:
                if flow_types.count(flow_type) > flow_types.count(most_common_type):
                    most_common_type = flow_type

            if "database" in str(most_common_type).lower():
                return "Database"
            elif "api" in str(most_common_type).lower():
                return "API"
            elif "queue" in str(most_common_type).lower():
                return "Queue"
            else:
                return str(most_common_type).title()

        return "Connection"

    def _relationship_type_to_label(self, rel_type: str) -> str:
        """Convert relationship type to display label."""
        type_mapping = {
            "database_connection": "Database",
            "api_call": "API",
            "message_producer": "Queue",
            "message_consumer": "Queue",
            "message_queue_connection": "Queue",
            "load_balancer_backend": "HTTP",
            "gateway_to_service": "Gateway"
        }

        return type_mapping.get(rel_type, rel_type.replace("_", " ").title())

    def _categorize_connections_by_type(self, connection_counts: Dict[Tuple[str, str], int],
                                        data_flows: List[Dict[str, Any]]) -> Dict[str, List[Tuple[Tuple[str, str], int]]]:
        """Categorize connections by type to ensure balanced representation in diagrams."""
        categorized: Dict[str, List[Tuple[Tuple[str, str], int]]] = {
            "database": [],
            "api": [],
            "infrastructure": [],
            "service": [],
            "other": []
        }

        # Create a lookup for flow types between components
        flow_type_lookup: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
        for flow in data_flows:
            source = self._clean_component_name(flow.get("source", ""))
            target = self._clean_component_name(flow.get("target", ""))
            flow_type = flow.get("type", "")
            category = flow.get("category", "")

            key = (source, target)
            if key not in flow_type_lookup:
                flow_type_lookup[key] = []
            flow_type_lookup[key].append((flow_type, category))

        # Categorize each connection
        for (source, target), count in connection_counts.items():
            conn_key = (source, target)
            flow_types = flow_type_lookup.get(conn_key, [])

            # Determine category based on flow types and patterns
            category = self._determine_connection_category(
                source, target, flow_types)
            categorized[category].append(((source, target), count))

        # Log categorization results
        for category, connections in categorized.items():
            if connections:
                self.config.logger.info(
                    f"Category '{category}': {len(connections)} connections")

        return categorized

    def _determine_connection_category(self, source: str, target: str,
                                       flow_types: List[Tuple[str, str]]) -> str:
        """Determine the category of a connection based on flow types and component names."""

        # Check flow types first (most reliable)
        for flow_type, category in flow_types:
            # Database connections
            if any(term in flow_type.lower() for term in ["database", "db", "sql", "postgres", "mysql", "redis", "mongodb"]):
                return "database"
            if category == "dependency" and any(term in flow_type.lower() for term in ["to_database", "to_cache"]):
                return "database"

            # API connections
            if any(term in flow_type.lower() for term in ["rest_", "api_", "graphql", "endpoint"]):
                return "api"
            if category == "api":
                return "api"

            # Infrastructure connections
            if any(term in flow_type.lower() for term in ["volume", "storage", "network", "load_balancer", "queue"]):
                return "infrastructure"

            # Service connections
            if any(term in flow_type.lower() for term in ["service_to_service", "service_"]):
                return "service"

        # Fallback to component name analysis
        source_lower = source.lower()
        target_lower = target.lower()

        # Database connections based on component names
        if any(term in target_lower for term in ["database", "db", "postgres", "mysql", "redis", "mongodb", "cache"]):
            return "database"
        if any(term in source_lower for term in ["database", "db", "postgres", "mysql", "redis", "mongodb", "cache"]):
            return "database"

        # API connections based on component names
        if "api" in source_lower or "api" in target_lower:
            return "api"

        # Infrastructure connections
        if any(term in target_lower for term in ["storage", "bucket", "volume", "queue", "kafka", "lb", "balancer"]):
            return "infrastructure"
        if any(term in source_lower for term in ["storage", "bucket", "volume", "queue", "kafka", "lb", "balancer"]):
            return "infrastructure"

        # Service connections
        if "service" in source_lower or "service" in target_lower:
            return "service"

        # Default to other
        return "other"

    def _find_component_match(self, name: str, all_names: set) -> str:
        """Find a matching component name in the diagram with enhanced fuzzy matching."""

        if not name or not all_names:
            return ""

        original_name = name

        # Direct match
        if name in all_names:
            self.config.logger.debug(f"Direct match: '{name}'")
            return name

        # Enhanced API service matching (try this early for API components)
        if "api" in name.lower():
            api_match = self._find_api_service_match(name, all_names)
            if api_match:
                self.config.logger.debug(
                    f"API service match: '{name}' → '{api_match}'")
                return api_match

        # Generate comprehensive name variations
        variations = self._generate_name_variations(name)

        # Try exact variations first
        for variation in variations:
            if variation in all_names:
                self.config.logger.debug(
                    f"Variation match: '{name}' → '{variation}'")
                return variation

        # Try API service matching again with variations if original didn't work
        if "api" not in name.lower():
            api_match = self._find_api_service_match(name, all_names)
            if api_match:
                self.config.logger.debug(
                    f"API service match (delayed): '{name}' → '{api_match}'")
                return api_match

        # Smart similarity matching with scoring
        best_match, confidence = self._find_similarity_match(name, all_names)
        if confidence > 0.6:  # Only accept high confidence matches
            self.config.logger.debug(
                f"Similarity match: '{name}' → '{best_match}' (confidence: {confidence:.2f})")
            return best_match
        elif confidence > 0.3:  # Log near misses for debugging
            self.config.logger.debug(
                f"Near miss: '{name}' → '{best_match}' (confidence: {confidence:.2f}, threshold: 0.6)")

        # Log complete failure for debugging
        self.config.logger.debug(
            f"No match found for: '{original_name}' (tried {len(variations)} variations)")
        return ""

    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate comprehensive variations of a component name."""
        if not name:
            return []

        variations = []
        cleaned_name = self._clean_component_name(name)

        # Basic transformations
        base_variations = [
            name,
            cleaned_name,
            name.lower(),
            cleaned_name.lower(),
            name.upper(),
            name.title(),
            name.replace("-", "_"),
            name.replace("_", "-"),
            name.replace(" ", "-"),
            name.replace(" ", "_"),
            name.replace("-", "").replace("_", ""),  # Remove separators
            cleaned_name.replace("-", "").replace("_", ""),
        ]

        # Add variations with common prefixes removed
        prefixes_to_remove = ["service_", "infra_", "api_", "app_", "web_"]
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                base_name = name[len(prefix):]
                base_variations.extend([
                    base_name,
                    base_name.lower(),
                    base_name.replace("-", "_"),
                    base_name.replace("_", "-"),
                    self._clean_component_name(base_name)
                ])

        # Add variations with common suffixes - especially important for API services
        base_names = [name, cleaned_name, name.lower(), cleaned_name.lower()]
        suffixes_to_add = ["", "-service", "_service",
                           " service", " API Service", "-API-Service"]

        for base in base_names:
            # Skip empty bases
            if not base:
                continue

            for suffix in suffixes_to_add:
                variation = f"{base}{suffix}"
                variations.append(variation)

                # Also add with normalized casing for API Service suffix
                if "api service" in variation.lower() and "api service" not in variation:
                    variations.append(variation.replace(
                        "API Service", "api service"))
                    variations.append(variation.replace(
                        "api service", "API Service"))

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for v in base_variations + variations:
            if v and v not in seen:
                seen.add(v)
                result.append(v)

        return result

    def _find_api_service_match(self, name: str, all_names: set) -> str:
        """Enhanced API service matching logic for specific patterns."""
        if not name or not all_names:
            return ""

        name_lower = name.lower()

        # Pattern 1: Handle "api_service-name" → "service-name API Service"
        if name_lower.startswith("api_"):
            service_name = name_lower[4:]  # Remove "api_" prefix
            service_name_normalized = service_name.replace("_", "-")

            # Look for exact matches first
            target_pattern = f"{service_name_normalized} api service"
            for component_name in all_names:
                if component_name.lower() == target_pattern:
                    self.config.logger.debug(
                        f"API exact match: '{name}' → '{component_name}'")
                    return str(component_name)

            # Look for partial matches
            for component_name in all_names:
                comp_lower = component_name.lower()
                if "api service" in comp_lower:
                    # Extract the service part before " API Service"
                    service_part = comp_lower.replace(
                        " api service", "").strip()

                    # Try various normalization approaches
                    if (service_part == service_name_normalized or
                        service_part == service_name.replace("-", "") or
                            service_part.replace("-", "") == service_name_normalized.replace("-", "")):
                        self.config.logger.debug(
                            f"API partial match: '{name}' → '{component_name}'")
                        return str(component_name)

        # Pattern 2: Direct API pattern matching (existing logic, improved)
        if any(api_term in name_lower for api_term in ["api", "service"]):
            # Look for exact API service matches
            for component_name in all_names:
                comp_lower = component_name.lower()
                if "api service" in comp_lower:
                    # Extract service identifier
                    service_part = comp_lower.replace(
                        " api service", "").strip()

                    # Normalize both names for comparison
                    name_normalized = name_lower.replace("api", "").replace(
                        "service", "").replace("-", " ").replace("_", " ").strip()
                    service_normalized = service_part.replace(
                        "-", " ").replace("_", " ").strip()

                    # Check various matching patterns
                    if (service_normalized == name_normalized or
                        service_normalized in name_normalized or
                        name_normalized in service_normalized or
                        service_part in name_lower or
                            name_lower.replace("-", "").replace("_", "") == service_part.replace("-", "").replace("_", "")):
                        self.config.logger.debug(
                            f"API service match: '{name}' → '{component_name}'")
                        return str(component_name)

        return ""

    def _find_similarity_match(self, name: str, all_names: set) -> tuple[str, float]:
        """Find the best match using similarity scoring."""
        best_match = ""
        best_confidence = 0.0

        name_lower = name.lower()
        name_normalized = name_lower.replace(
            "-", "").replace("_", "").replace(" ", "")

        for component_name in all_names:
            comp_lower = component_name.lower()
            comp_normalized = comp_lower.replace(
                "-", "").replace("_", "").replace(" ", "")

            # Skip very short names to avoid false positives
            if len(name_normalized) < 3 or len(comp_normalized) < 3:
                continue

            confidence = self._calculate_similarity(
                name_normalized, comp_normalized, name_lower, comp_lower)

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = component_name

        return best_match, best_confidence

    def _calculate_similarity(self, name_norm: str, comp_norm: str, name_orig: str, comp_orig: str) -> float:
        """Calculate similarity score between two component names."""
        # Exact normalized match
        if name_norm == comp_norm:
            return 1.0

        # Substring matching with higher weight for longer matches
        if name_norm in comp_norm or comp_norm in name_norm:
            overlap_len = max(len(name_norm), len(comp_norm))
            return 0.7 + (0.2 * overlap_len / max(len(name_norm), len(comp_norm)))

        # Common prefix/suffix scoring
        prefix_score = 0.0
        suffix_score = 0.0

        # Check for common prefixes
        for i in range(1, min(len(name_norm), len(comp_norm)) + 1):
            if name_norm[:i] == comp_norm[:i]:
                prefix_score = i / max(len(name_norm), len(comp_norm))

        # Check for common suffixes
        for i in range(1, min(len(name_norm), len(comp_norm)) + 1):
            if name_norm[-i:] == comp_norm[-i:]:
                suffix_score = i / max(len(name_norm), len(comp_norm))

        # Token-based matching (split by common separators)
        name_tokens = set(name_orig.replace(
            "-", " ").replace("_", " ").split())
        comp_tokens = set(comp_orig.replace(
            "-", " ").replace("_", " ").split())

        if name_tokens and comp_tokens:
            token_overlap = len(name_tokens.intersection(comp_tokens))
            token_total = len(name_tokens.union(comp_tokens))
            token_score = token_overlap / token_total if token_total > 0 else 0.0
        else:
            token_score = 0.0

        # Combine scores with weights
        final_score = max(prefix_score * 0.3, suffix_score *
                          0.3, token_score * 0.4)

        return final_score

    def _analyze_missing_components(self, data_flows: List[Dict], available_components: set) -> None:
        """Analyze which components from data flows are missing from the diagram."""
        missing_sources = set()
        missing_targets = set()
        flow_component_counts: Dict[str, int] = {}

        for flow in data_flows:
            source = flow.get("source", "")
            target = flow.get("target", "")

            if source and source != "external":
                cleaned_source = self._clean_component_name(source)
                if not self._find_component_match(cleaned_source, available_components):
                    missing_sources.add(source)
                    flow_component_counts[source] = flow_component_counts.get(
                        source, 0) + 1

            if target and target != "external":
                cleaned_target = self._clean_component_name(target)
                if not self._find_component_match(cleaned_target, available_components):
                    missing_targets.add(target)
                    flow_component_counts[target] = flow_component_counts.get(
                        target, 0) + 1

        # Report the most frequently referenced missing components
        if missing_sources or missing_targets:
            self.config.logger.warning(
                f"Found {len(missing_sources)} missing source components and {len(missing_targets)} missing target components")

            # Show top missing components by frequency
            sorted_missing = sorted(
                flow_component_counts.items(), key=lambda x: x[1], reverse=True)
            top_missing = sorted_missing[:10]

            self.config.logger.warning(
                "Top missing components by flow frequency:")
            for component, count in top_missing:
                cleaned = self._clean_component_name(component)
                self.config.logger.warning(
                    f"  {component} (cleaned: {cleaned}) - referenced in {count} flows")
