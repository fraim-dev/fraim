# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Data Flow Analyzer

Handles extraction, deduplication, and enrichment of data flows from
infrastructure and API discovery results.
"""

from typing import Any, Dict, List

from fraim.config import Config

from .types import ComponentDiscoveryResults


class DataFlowAnalyzer:
    """Analyzes and extracts data flows from component discovery results."""

    def __init__(self, config: Config):
        self.config = config

    async def analyze_data_flows(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Main entry point for data flow analysis."""
        try:
            data_flows = []

            # Extract data flows from infrastructure
            if results.infrastructure:
                infra_flows = self._extract_infrastructure_data_flows(results.infrastructure)
                data_flows.extend(infra_flows)

            # Extract data flows from API interfaces
            if results.api_interfaces:
                api_flows = self._extract_api_data_flows(results.api_interfaces)
                data_flows.extend(api_flows)

            # Deduplicate and enrich flows
            enriched_flows = self._deduplicate_and_enrich_flows(data_flows)

            self.config.logger.info(f"Analyzed {len(enriched_flows)} total data flows")
            return enriched_flows

        except Exception as e:
            self.config.logger.error(f"Data flow analysis failed: {str(e)}")
            return []

    def _extract_infrastructure_data_flows(self, infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data flows from infrastructure discovery."""
        flows = []

        try:
            self.config.logger.info(f"Processing infrastructure data: {type(infrastructure)}")

            # Extract flows from container configurations
            if "container_configs" in infrastructure:
                containers = infrastructure["container_configs"]
                self.config.logger.info(f"Found {len(containers)} container configs")

                for i, container in enumerate(containers):
                    try:
                        self.config.logger.info(f"Processing container {i}: {type(container)}")

                        if isinstance(container, dict):
                            # Extract flows from exposed ports
                            exposed_ports = container.get("exposed_ports", [])
                            self.config.logger.info(
                                f"Container {i} exposed_ports: {type(exposed_ports)} - {exposed_ports}"
                            )

                            for port in exposed_ports:
                                flow = {
                                    "source": container.get("container_name", "unknown"),
                                    "target": "external",
                                    "type": "container_port_exposure",
                                    "category": "infrastructure",
                                    "protocol": "TCP",
                                    "port": port,
                                    "direction": "bidirectional",
                                    "data_classification": "application_data",
                                    "encryption": False,
                                    "authentication": "unknown",
                                    "metadata": {
                                        "container_name": container.get("container_name"),
                                        "base_image": container.get("base_image"),
                                        "runtime": container.get("runtime", "unknown"),
                                    },
                                }
                                flows.append(flow)

                            # Extract flows from volume mounts
                            volume_mounts = container.get("volume_mounts", [])
                            self.config.logger.info(
                                f"Container {i} volume_mounts: {type(volume_mounts)} - {volume_mounts}"
                            )

                            for volume in volume_mounts:
                                # volume_mounts is an array of strings, not dictionaries
                                if isinstance(volume, str):
                                    flow = {
                                        "source": container.get("container_name", "unknown"),
                                        "target": f"volume_{volume.replace('/', '_')}",
                                        "type": "volume_mount",
                                        "category": "infrastructure",
                                        "protocol": "filesystem",
                                        "port": None,
                                        "direction": "bidirectional",
                                        "data_classification": "persistent_data",
                                        "encryption": False,
                                        "authentication": "filesystem_level",
                                        "metadata": {
                                            "mount_path": volume,
                                            "access_mode": "ReadWrite",  # Default
                                        },
                                    }
                                    flows.append(flow)
                    except Exception as container_error:
                        self.config.logger.error(f"Error processing container {i}: {str(container_error)}")
                        continue

            # Extract flows from infrastructure components
            if "infrastructure_components" in infrastructure:
                components = infrastructure["infrastructure_components"]
                self.config.logger.info(f"Found {len(components)} infrastructure components")

                for i, component in enumerate(components):
                    try:
                        self.config.logger.info(f"Processing component {i}: {type(component)}")

                        if isinstance(component, dict):
                            # Create flows for load balancers
                            if component.get("type") == "load_balancer":
                                # Handle configuration field which might be string or dict
                                config = component.get("configuration", {})
                                ssl_enabled = False
                                if isinstance(config, dict):
                                    ssl_enabled = config.get("ssl_enabled", False)
                                elif isinstance(config, str):
                                    ssl_enabled = "ssl" in config.lower() or "tls" in config.lower()

                                flow = {
                                    "source": "external",
                                    "target": component.get("name", "unknown_lb"),
                                    "type": "load_balancer_ingress",
                                    "category": "infrastructure",
                                    "protocol": "HTTP",
                                    "port": 80,
                                    "direction": "unidirectional",
                                    "data_classification": "application_data",
                                    "encryption": ssl_enabled,
                                    "authentication": "unknown",
                                    "metadata": {
                                        "provider": component.get("provider"),
                                        "service_name": component.get("service_name"),
                                        "environment": component.get("environment"),
                                    },
                                }
                                flows.append(flow)

                            # Create flows for databases
                            elif component.get("type") in ["database", "rds", "dynamodb"]:
                                # Handle configuration field which might be string or dict
                                config = component.get("configuration", {})
                                encrypted = False
                                if isinstance(config, dict):
                                    encrypted = config.get("encrypted", False)
                                elif isinstance(config, str):
                                    encrypted = "encrypt" in config.lower() or "ssl" in config.lower()

                                flow = {
                                    "source": "application",
                                    "target": component.get("name", "unknown_db"),
                                    "type": "database_connection",
                                    "category": "infrastructure",
                                    "protocol": "SQL",
                                    "port": 5432,  # Default, could be enhanced
                                    "direction": "bidirectional",
                                    "data_classification": "persistent_data",
                                    "encryption": encrypted,
                                    "authentication": "database_auth",
                                    "metadata": {
                                        "provider": component.get("provider"),
                                        "service_name": component.get("service_name"),
                                        "environment": component.get("environment"),
                                    },
                                }
                                flows.append(flow)
                    except Exception as component_error:
                        self.config.logger.error(f"Error processing component {i}: {str(component_error)}")
                        continue

            # Extract flows from deployment environments
            if "deployment_environments" in infrastructure:
                environments = infrastructure["deployment_environments"]
                self.config.logger.info(f"Found {len(environments)} deployment environments")

                for i, env in enumerate(environments):
                    try:
                        self.config.logger.info(f"Processing environment {i}: {type(env)}")

                        if isinstance(env, dict):
                            # Create flows for services within environments
                            services = env.get("services", [])
                            self.config.logger.info(f"Environment {i} services: {type(services)} - {services}")

                            for j, service1 in enumerate(services):
                                for service2 in services[j + 1 :]:
                                    if isinstance(service1, dict) and isinstance(service2, dict):
                                        flow = {
                                            "source": service1.get("name", "unknown_service"),
                                            "target": service2.get("name", "unknown_service"),
                                            "type": "service_communication",
                                            "category": "infrastructure",
                                            "protocol": "HTTP",
                                            "port": service2.get("port", 8080),
                                            "direction": "bidirectional",
                                            "data_classification": "application_data",
                                            "encryption": False,
                                            "authentication": "service_level",
                                            "metadata": {
                                                "environment": env.get("name"),
                                                "namespace": env.get("namespace"),
                                            },
                                        }
                                        flows.append(flow)
                    except Exception as env_error:
                        self.config.logger.error(f"Error processing environment {i}: {str(env_error)}")
                        continue

            self.config.logger.info(f"Successfully extracted {len(flows)} infrastructure data flows")
            return flows

        except Exception as e:
            self.config.logger.error(f"Error extracting infrastructure data flows: {str(e)}")
            import traceback

            self.config.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_api_data_flows(self, api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data flows from API interface discovery."""
        flows = []

        try:
            # Extract flows from REST endpoints
            if "rest_endpoints" in api_interfaces:
                endpoints = api_interfaces["rest_endpoints"]
                for endpoint in endpoints:
                    if isinstance(endpoint, dict):
                        # Create flow for each endpoint
                        flow = {
                            "source": "client",
                            "target": endpoint.get("service_name", "unknown_service"),
                            "type": "api_call",
                            "category": "api",
                            "protocol": "HTTP",
                            "port": 443 if endpoint.get("requires_auth", False) else 80,
                            "direction": "bidirectional",
                            "data_classification": self._classify_endpoint_data(endpoint),
                            # Assume HTTPS if auth required
                            "encryption": endpoint.get("requires_auth", False),
                            "authentication": endpoint.get("auth_type", "unknown"),
                            "metadata": {
                                "method": endpoint.get("http_method"),
                                "path": endpoint.get("endpoint_path"),
                                "service_name": endpoint.get("service_name"),
                                "owasp_risks": endpoint.get("owasp_risks", []),
                            },
                        }
                        flows.append(flow)

            # Extract flows from GraphQL schema
            if "graphql_schema" in api_interfaces:
                graphql_fields = api_interfaces["graphql_schema"]
                for field in graphql_fields:
                    if isinstance(field, dict):
                        flow = {
                            "source": "client",
                            "target": "graphql_service",
                            "type": "graphql_query",
                            "category": "api",
                            "protocol": "HTTP",
                            "port": 443,
                            "direction": "bidirectional",
                            "data_classification": self._classify_graphql_data(field),
                            "encryption": True,  # GraphQL typically uses HTTPS
                            "authentication": field.get("requires_auth", "unknown"),
                            "metadata": {
                                "field_name": field.get("field_name"),
                                "field_type": field.get("field_type"),
                                "operation_type": field.get("operation_type"),
                            },
                        }
                        flows.append(flow)

            # Extract flows from WebSocket connections
            if "websocket_connections" in api_interfaces:
                websockets = api_interfaces["websocket_connections"]
                for ws in websockets:
                    if isinstance(ws, dict):
                        flow = {
                            "source": "client",
                            "target": ws.get("service_name", "websocket_service"),
                            "type": "websocket_connection",
                            "category": "api",
                            "protocol": "WebSocket",
                            "port": 443,
                            "direction": "bidirectional",
                            "data_classification": "real_time_data",
                            "encryption": True,
                            "authentication": ws.get("auth_required", "unknown"),
                            "metadata": {
                                "endpoint": ws.get("endpoint"),
                                "protocol": ws.get("protocol"),
                                "broadcasting": ws.get("broadcasting"),
                            },
                        }
                        flows.append(flow)

            # Extract flows from existing data flows (if already identified by API discovery)
            if "data_flows" in api_interfaces:
                existing_flows = api_interfaces["data_flows"]
                for existing_flow in existing_flows:
                    if isinstance(existing_flow, dict):
                        flow = {
                            "source": existing_flow.get("source", "unknown"),
                            "target": existing_flow.get("destination", "unknown"),
                            "type": "api_data_flow",
                            "category": "api",
                            "protocol": "HTTP",
                            "port": None,
                            "direction": "bidirectional",
                            "data_classification": self._classify_flow_data(existing_flow),
                            "encryption": True,
                            "authentication": "unknown",
                            "metadata": {
                                "flow_name": existing_flow.get("flow_name"),
                                "data_format": existing_flow.get("data_format"),
                                "transformation_logic": existing_flow.get("transformation_logic"),
                                "error_handling": existing_flow.get("error_handling"),
                            },
                        }
                        flows.append(flow)

            self.config.logger.info(f"Extracted {len(flows)} API data flows")
            return flows

        except Exception as e:
            self.config.logger.error(f"Error extracting API data flows: {str(e)}")
            return []

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
