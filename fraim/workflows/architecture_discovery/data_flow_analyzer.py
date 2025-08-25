# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Data Flow Analyzer

Analyzes data flows between unified system components, replacing the previous
fragmented approach that worked with separate infrastructure and API results.
"""

from typing import Any, Dict, List, Optional

from fraim.config import Config

from .types import ComponentDiscoveryResults, UnifiedComponent
from .port_protocol_mapper import PortProtocolMapper, DataClassification
from .flow_analysis_config import get_environment_config
from .client_discovery import ClientDiscoveryService


class DataFlowAnalyzer:
    """Analyzes data flows between unified system components."""

    def __init__(self, config: Config, project_root: Optional[str] = None):
        self.config = config

        # Determine analysis environment from config or default to production
        analysis_env = getattr(config, 'analysis_environment', 'production')
        analysis_config = get_environment_config(analysis_env)

        # Initialize port mapper with IaC extraction capability
        self.port_mapper = PortProtocolMapper(analysis_config, project_root)

        # Initialize client discovery service
        self.client_discovery = ClientDiscoveryService(config)

        # Store all components for client discovery
        self.all_components: List[UnifiedComponent] = []

    async def analyze_data_flows(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Main entry point for data flow analysis using unified components."""
        try:
            # Log port mapping configuration and IaC extraction results
            self.port_mapper.log_port_assumptions(self.config.logger)
            self._log_iac_extraction_results()

            data_flows = []

            # Primary approach: Extract data flows from unified components
            if results.unified_components and results.unified_components.components:
                # Store components for client discovery
                self.all_components = results.unified_components.components.copy()

                self.config.logger.info(
                    f"Analyzing data flows between {len(results.unified_components.components)} unified components")

                # Extract flows using original components (includes all existing relationships)
                unified_flows = self._extract_unified_component_data_flows(
                    results.unified_components.components)
                data_flows.extend(unified_flows)

                # After flow extraction, integrate any generated clients back into results
                # This ensures they appear in diagrams without disrupting existing connections
                generated_clients = self.client_discovery.get_generated_clients()
                if generated_clients:
                    self.config.logger.info(
                        f"Integrating {len(generated_clients)} generated client components")
                    results.unified_components.components.extend(
                        generated_clients)
                    # Don't add to self.all_components here to avoid affecting subsequent processing
            else:
                raise Exception(
                    "Required dependency not found: unified components")

            # Deduplicate and enrich flows
            enriched_flows = self._deduplicate_and_enrich_flows(data_flows)

            self.config.logger.info(f"Analyzed {len(enriched_flows)} total data flows")

            # Log client discovery summary
            client_summary = self.client_discovery.get_client_summary()
            self.config.logger.info(f"Client Discovery Summary: "
                                    f"APIs processed: {client_summary['total_apis_processed']}, "
                                    f"Clients found: {client_summary['total_clients_discovered']}, "
                                    f"Explicit: {client_summary['explicit_clients_found']}, "
                                    f"Generated: {client_summary['generated_clients_created']}")

            # Log any unreliable port mappings used
            self._log_port_reliability_warnings(enriched_flows)

            return enriched_flows

        except Exception as e:
            self.config.logger.error(f"Data flow analysis failed: {str(e)}")
            return []

    def _extract_unified_component_data_flows(self, components: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Extract data flows from unified components by analyzing their connectivity and relationships."""
        flows = []

        try:
            # Create component lookup for relationship analysis
            component_map = {comp.component_id: comp for comp in components}

            # 1. Extract flows from component network exposure (ports, endpoints)
            for component in components:
                flows.extend(self._extract_component_network_flows(component))

            # 2. Extract flows from explicit dependencies and relationships
            for component in components:
                flows.extend(self._extract_component_relationship_flows(
                    component, component_map))

            # 3. Extract flows from API interfaces
            for component in components:
                flows.extend(self._extract_component_api_flows(component))

            # 4. Extract flows from infrastructure deployment details
            for component in components:
                flows.extend(
                    self._extract_component_infrastructure_flows(component))

            self.config.logger.info(
                f"Extracted {len(flows)} data flows from {len(components)} unified components")
            return flows

        except Exception as e:
            self.config.logger.error(
                f"Error extracting unified component data flows: {str(e)}")
            return []

    def _extract_component_network_flows(self, component: UnifiedComponent) -> List[Dict[str, Any]]:
        """Extract data flows based on component's network exposure (ports, endpoints)."""
        flows = []

        # Analyze exposed ports
        for port in component.exposed_ports:
            port_info = self.port_mapper.analyze_port_with_iac_priority(
                port, component.component_name, None
            )

            flow = {
                "source": "external" if port_info.direction == "inbound" else component.component_id,
                "target": component.component_id if port_info.direction == "inbound" else "external",
                "type": f"{component.component_type}_port_exposure",
                "category": "network",
                "protocol": port_info.protocol,
                "port": port,
                "direction": port_info.direction,
                "data_classification": port_info.data_classification.value,
                "encryption": port_info.default_encryption,
                "authentication": port_info.typical_auth,
                "metadata": {
                    "component_name": component.component_name,
                    "component_type": component.component_type,
                    "service_type": port_info.service_name,
                    "security_level": port_info.security_level.value,
                    "protocols": component.protocols,
                },
            }
            flows.append(flow)

        # Analyze public endpoints
        for endpoint in component.endpoints:
            # Extract protocol and port from endpoint URL
            protocol = "HTTPS" if endpoint.startswith("https://") else "HTTP"
            port = 443 if protocol == "HTTPS" else 80

            flow = {
                "source": "external",
                "target": component.component_id,
                "type": f"{component.component_type}_endpoint_access",
                "category": "api",
                "protocol": protocol,
                "port": port,
                "direction": "inbound",
                "data_classification": "public",
                "encryption": protocol == "HTTPS",
                "authentication": "varies",  # Would depend on specific endpoint
                "metadata": {
                    "component_name": component.component_name,
                    "component_type": component.component_type,
                    "endpoint_url": endpoint,
                },
            }
            flows.append(flow)

        return flows

    def _extract_component_relationship_flows(self, component: UnifiedComponent, component_map: Dict[str, UnifiedComponent]) -> List[Dict[str, Any]]:
        """Extract data flows based on explicit component dependencies and relationships."""
        flows = []

        # Analyze dependencies (this component depends on others)
        for dep_id in component.dependencies:
            if dep_id in component_map:
                target_comp = component_map[dep_id]

                # Infer communication details based on component types
                flow_info = self._infer_component_communication(
                    component, target_comp)

                flow = {
                    "source": component.component_id,
                    "target": dep_id,
                    "type": f"{component.component_type}_to_{target_comp.component_type}",
                    "category": "dependency",
                    "protocol": flow_info.get("protocol", "TCP"),
                    "port": flow_info.get("port"),
                    "direction": "unidirectional",
                    "data_classification": flow_info.get("data_classification", "internal"),
                    "encryption": flow_info.get("encryption", False),
                    "authentication": flow_info.get("authentication", "service_to_service"),
                    "metadata": {
                        "source_component": component.component_name,
                        "source_type": component.component_type,
                        "target_component": target_comp.component_name,
                        "target_type": target_comp.component_type,
                        "relationship": "dependency",
                    },
                }
                flows.append(flow)

        return flows

    def _extract_component_api_flows(self, component: UnifiedComponent) -> List[Dict[str, Any]]:
        """Extract data flows from component's API interfaces using hybrid client discovery."""
        flows: List[Dict[str, Any]] = []

        if not component.api_interfaces:
            return flows

        # Discover actual client components for this API service
        client_components = self.client_discovery.discover_api_clients(
            component, self.all_components)

        if not client_components:
            self.config.logger.warning(
                f"No clients found for API component {component.component_name}")
            return flows

        for api_interface in component.api_interfaces:
            api_type = api_interface.get("type", "unknown")

            if api_type == "rest":
                endpoints = api_interface.get("endpoints", [])
                for endpoint in endpoints:
                    # Create flow for each REST endpoint from each discovered client
                    method = endpoint.get("http_method", "GET")
                    protocol = "HTTPS" if endpoint.get(
                        "ssl_enabled", False) else "HTTP"

                    for client_comp in client_components:
                        flow = {
                            "source": client_comp.component_id,  # Use actual client component ID
                            "target": component.component_id,
                            "type": f"rest_{method.lower()}",
                            "category": "api",
                            "protocol": protocol,
                            "port": 443 if protocol == "HTTPS" else 80,
                            "direction": "inbound",
                            "data_classification": self._classify_endpoint_data(endpoint),
                            "encryption": protocol == "HTTPS",
                            "authentication": endpoint.get("authentication", "unknown"),
                            "metadata": {
                                "component_name": component.component_name,
                                "client_name": client_comp.component_name,
                                "client_type": client_comp.component_type,
                                "endpoint_path": endpoint.get("endpoint_path", ""),
                                "http_method": method,
                                "api_type": "REST",
                                "client_generated": client_comp.metadata and client_comp.metadata.get("generated", False),
                            },
                        }
                        flows.append(flow)

            # Handle GraphQL, WebSocket, and other API types similarly
            elif api_type == "graphql":
                for client_comp in client_components:
                    flow = {
                        "source": client_comp.component_id,  # Use actual client component ID
                        "target": component.component_id,
                        "type": "graphql_query",
                        "category": "api",
                        "protocol": "HTTPS",
                        "port": 443,
                        "direction": "bidirectional",
                        "data_classification": "varies",
                        "encryption": True,
                        "authentication": "varies",
                        "metadata": {
                            "component_name": component.component_name,
                            "client_name": client_comp.component_name,
                            "client_type": client_comp.component_type,
                            "api_type": "GraphQL",
                            "client_generated": client_comp.metadata and client_comp.metadata.get("generated", False),
                        },
                    }
                    flows.append(flow)

        return flows

    def _extract_component_infrastructure_flows(self, component: UnifiedComponent) -> List[Dict[str, Any]]:
        """Extract data flows from component's infrastructure deployment details."""
        flows = []

        # Analyze deployment information (container volumes, etc.)
        if component.deployment_info:
            volume_mounts = component.deployment_info.get("volume_mounts", [])
            for volume in volume_mounts:
                if isinstance(volume, str):
                    data_class = self._classify_volume_data(volume)
                    encryption = self._detect_volume_encryption(
                        volume, component.deployment_info)

                    flow = {
                        "source": component.component_id,
                        "target": f"volume_{volume.replace('/', '_')}",
                        "type": "volume_mount",
                        "category": "infrastructure",
                        "protocol": "filesystem",
                        "port": None,
                        "direction": "bidirectional",
                        "data_classification": data_class,
                        "encryption": encryption,
                        "authentication": "filesystem_level",
                        "metadata": {
                            "component_name": component.component_name,
                            "component_type": component.component_type,
                            "mount_path": volume,
                            "access_mode": "ReadWrite",  # Default
                        },
                    }
                    flows.append(flow)

        return flows

    def _infer_component_communication(self, source: UnifiedComponent, target: UnifiedComponent) -> Dict[str, Any]:
        """Infer communication details between two components based on their types."""
        communication = {}

        # Database connections
        if target.component_type in ["database", "cache"]:
            if "postgres" in target.component_name.lower():
                communication.update(
                    {"protocol": "TCP", "port": 5432, "encryption": True})
            elif "mysql" in target.component_name.lower():
                communication.update(
                    {"protocol": "TCP", "port": 3306, "encryption": True})
            elif "redis" in target.component_name.lower():
                communication.update(
                    {"protocol": "TCP", "port": 6379, "encryption": False})
            elif "mongodb" in target.component_name.lower():
                communication.update(
                    {"protocol": "TCP", "port": 27017, "encryption": True})
            else:
                # Default database assumptions
                communication.update(
                    {"protocol": "TCP", "port": 5432, "encryption": True})

            communication.update({
                "data_classification": "sensitive",
                "authentication": "database_credentials"
            })

        # Service-to-service communication
        elif target.component_type == "service":
            communication.update({
                "protocol": "HTTPS" if "https" in target.protocols else "HTTP",
                "port": 443 if "https" in target.protocols else 80,
                "encryption": "https" in target.protocols,
                "data_classification": "internal",
                "authentication": "service_token"
            })

        # Load balancer communication
        elif target.component_type == "load_balancer":
            communication.update({
                "protocol": "HTTPS",
                "port": 443,
                "encryption": True,
                "data_classification": "public",
                "authentication": "none"
            })

        # Queue/messaging systems
        elif target.component_type == "queue":
            communication.update({
                "protocol": "AMQP",
                "port": 5672,
                "encryption": True,
                "data_classification": "internal",
                "authentication": "queue_credentials"
            })

        # Default assumptions
        else:
            communication.update({
                "protocol": "TCP",
                "port": None,
                "encryption": False,
                "data_classification": "internal",
                "authentication": "unknown"
            })

        return communication

    def _classify_endpoint_data(self, endpoint: Dict[str, Any]) -> str:
        """Classify data sensitivity based on endpoint characteristics."""
        # Check for sensitive data indicators
        path = endpoint.get("endpoint_path", "").lower()

        if any(term in path for term in ["password", "secret", "token", "key"]):
            return "sensitive"
        elif any(term in path for term in ["user", "profile", "account", "personal"]):
            return "confidential"
        elif endpoint.get("requires_auth", False):
            return "internal"
        else:
            return "public"

    def _classify_graphql_data(self, field: Dict[str, Any]) -> str:
        """Classify data sensitivity for GraphQL fields."""
        field_name = field.get("field_name", "").lower()

        if any(term in field_name for term in ["password", "secret", "token"]):
            return "sensitive"
        elif field.get("requires_auth", False):
            return "confidential"
        else:
            return "internal"

    def _classify_flow_data(self, flow: Dict[str, Any]) -> str:
        """Classify data sensitivity for existing flows."""
        flow_name = flow.get("flow_name", "").lower()

        if any(term in flow_name for term in ["auth", "payment", "personal"]):
            return "confidential"
        else:
            return "internal"

    def _deduplicate_and_enrich_flows(self, flows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and enrich data flows."""
        try:
            # Create a set to track unique flows
            unique_flows = {}

            for flow in flows:
                # Create a unique key for the flow
                flow_key = self._create_flow_key(flow)

                if flow_key not in unique_flows:
                    # First time seeing this flow
                    unique_flows[flow_key] = flow.copy()
                else:
                    # Merge with existing flow
                    existing_flow = unique_flows[flow_key]
                    merged_flow = self._merge_flows(existing_flow, flow)
                    unique_flows[flow_key] = merged_flow

            # Enrich flows with additional context
            enriched_flows = []
            for flow in unique_flows.values():
                enriched_flow = self._enrich_flow(flow)
                enriched_flows.append(enriched_flow)

            self.config.logger.info(f"Deduplicated to {len(enriched_flows)} unique flows")
            return enriched_flows

        except Exception as e:
            self.config.logger.error(f"Error deduplicating flows: {str(e)}")
            return flows

    def _create_flow_key(self, flow: Dict[str, Any]) -> str:
        """Create a unique key for flow deduplication."""
        source = flow.get("source", "unknown")
        target = flow.get("target", "unknown")
        protocol = flow.get("protocol", "unknown")
        port = flow.get("port", "none")
        return f"{source}:{target}:{protocol}:{port}"

    def _merge_flows(self, flow1: Dict[str, Any], flow2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two flows with the same key."""
        merged = flow1.copy()

        # Merge metadata
        metadata1 = flow1.get("metadata", {})
        metadata2 = flow2.get("metadata", {})
        merged_metadata = {**metadata1, **metadata2}
        merged["metadata"] = merged_metadata

        # Use more specific encryption and authentication info
        if flow2.get("encryption", False) and not flow1.get("encryption", False):
            merged["encryption"] = flow2["encryption"]

        if flow2.get("authentication") != "unknown" and flow1.get("authentication") == "unknown":
            merged["authentication"] = flow2["authentication"]

        # Use more specific data classification
        if flow2.get("data_classification") != "unknown" and flow1.get("data_classification") == "unknown":
            merged["data_classification"] = flow2["data_classification"]

        return merged

    def _enrich_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich flow with additional context and risk assessment."""
        enriched = flow.copy()

        # Add risk assessment
        enriched["risk_level"] = self._assess_flow_risk(flow)

        # Add flow criticality
        enriched["criticality"] = self._assess_flow_criticality(flow)

        # Add security posture
        enriched["security_posture"] = self._assess_security_posture(flow)

        return enriched

    def _assess_flow_risk(self, flow: Dict[str, Any]) -> str:
        """Assess the risk level of a data flow."""
        risk_score = 0

        # Check encryption
        if not flow.get("encryption", False):
            risk_score += 2

        # Check authentication
        auth = flow.get("authentication", "unknown")
        if auth in ["none", "unknown"]:
            risk_score += 2
        elif auth in ["basic", "api_key"]:
            risk_score += 1

        # Check data classification
        data_class = flow.get("data_classification", "unknown")
        if data_class in ["sensitive", "confidential", "persistent_data"]:
            risk_score += 1

        # Check external flows
        if flow.get("category") == "external":
            risk_score += 1

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    def _assess_flow_criticality(self, flow: Dict[str, Any]) -> str:
        """Assess the criticality of a data flow."""
        # Database connections are typically critical
        if flow.get("type") == "database_connection":
            return "high"

        # Load balancer flows are important
        if flow.get("type") == "load_balancer_backend":
            return "high"

        # API flows might be medium criticality
        if flow.get("category") == "api":
            return "medium"

        return "medium"

    def _assess_security_posture(self, flow: Dict[str, Any]) -> str:
        """Assess the overall security posture of a flow."""
        if flow.get("encryption", False) and flow.get("authentication") not in ["none", "unknown"]:
            return "good"
        elif flow.get("encryption", False) or flow.get("authentication") not in ["none", "unknown"]:
            return "fair"
        else:
            return "poor"

    # Helper methods for infrastructure analysis
    def _subnets_can_communicate(self, subnet1: Dict[str, Any], subnet2: Dict[str, Any]) -> bool:
        """Check if two subnets can communicate based on routing rules."""
        # Simple heuristic: subnets in same VPC or with public access can communicate
        if subnet1.get("vpc_id") == subnet2.get("vpc_id"):
            return True
        if subnet1.get("public", False) and subnet2.get("public", False):
            return True
        return False

    def _lb_targets_instance(self, lb: Dict[str, Any], instance: Dict[str, Any]) -> bool:
        """Check if load balancer targets a specific instance."""
        # Simple heuristic: check if instance is in LB target group or same subnet
        lb_targets = lb.get("target_group", [])
        instance_id = instance.get("id") or instance.get("name")

        if instance_id in lb_targets:
            return True

        # Check if in same subnet (common pattern)
        if lb.get("subnet") == instance.get("subnet"):
            return True

        return False

    def _classify_volume_data(self, volume_path: str) -> str:
        """Classify data sensitivity based on volume mount path."""
        path_lower = volume_path.lower()

        if any(term in path_lower for term in ["/etc", "/config", "/secrets", "/certs"]):
            return DataClassification.RESTRICTED.value
        elif any(term in path_lower for term in ["/data", "/db", "/database", "/postgres", "/mysql"]):
            return DataClassification.CONFIDENTIAL.value
        elif any(term in path_lower for term in ["/logs", "/tmp", "/temp"]):
            return DataClassification.INTERNAL.value
        elif any(term in path_lower for term in ["/var/lib", "/usr/share", "/opt"]):
            return DataClassification.INTERNAL.value
        else:
            return DataClassification.INTERNAL.value

    def _detect_volume_encryption(self, volume_path: str, container_config: Dict[str, Any]) -> bool:
        """Detect if a volume mount is likely encrypted."""
        path_lower = volume_path.lower()

        # Check if it's a security-related mount that should be encrypted
        if any(term in path_lower for term in ["/etc/ssl", "/certs", "/secrets", "/keys"]):
            return True

        # Check container environment for encryption hints
        env_vars = container_config.get("environment_variables", [])
        for var in env_vars:
            var_lower = str(var).lower()
            if any(term in var_lower for term in ["encrypt", "ssl", "tls"]):
                return True

                # Check if base image suggests encryption capability
        base_image = container_config.get("base_image", "").lower()
        if any(term in base_image for term in ["secure", "encrypted"]):
            return True

        return False

    def _log_port_reliability_warnings(self, flows: List[Dict[str, Any]]) -> None:
        """Log warnings for flows using unreliable port mappings."""
        unreliable_ports = set()

        for flow in flows:
            port = flow.get("port")
            if port:
                is_reliable, explanation = self.port_mapper.is_port_mapping_reliable(
                    port)
                if not is_reliable:
                    unreliable_ports.add((port, explanation))

        if unreliable_ports:
            self.config.logger.warning(
                "Some data flows use ports with uncertain mappings:")
            for port, explanation in sorted(unreliable_ports):
                self.config.logger.warning(f"  {explanation}")
            self.config.logger.warning(
                "Consider verifying these port mappings for your specific environment"
            )

    def _log_iac_extraction_results(self) -> None:
        """Log information about IaC port extraction results."""
        if not self.port_mapper.iac_mappings:
            self.config.logger.warning(
                "No IaC port mappings found - relying on standards and inference")
            return

        total_services = len(self.port_mapper.iac_mappings)
        total_mappings = sum(len(mappings)
                             for mappings in self.port_mapper.iac_mappings.values())

        self.config.logger.info(f"IaC Port Mappings:")
        self.config.logger.info(
            f"  Services with explicit port mappings: {total_services}")
        self.config.logger.info(
            f"  Total port mappings found: {total_mappings}")

        # Log the services we have explicit mappings for
        for service_name, mappings in self.port_mapper.iac_mappings.items():
            ports = [str(m.container_port) for m in mappings]
            sources = list(set(m.source.value for m in mappings))
            self.config.logger.info(
                f"  {service_name}: ports {', '.join(ports)} (from {', '.join(sources)})")

    def _classify_mapping_source(self, flow: Dict[str, Any]) -> str:
        """Classify whether a flow's port mapping came from IaC or assumptions."""
        service_name = flow.get("source")
        port = flow.get("port")

        if service_name and service_name in self.port_mapper.iac_mappings:
            mappings = self.port_mapper.iac_mappings[service_name]
            for mapping in mappings:
                if mapping.container_port == port:
                    return f"iac_{mapping.source.value}"

        # Check if we have a standards-based mapping
        if port:
            standard = self.port_mapper.port_registry.get_port_standard(port)
            if standard:
                return f"standard_{standard.standard_level.value}"

        return "inferred"
