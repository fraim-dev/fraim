# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
External Integration Analyzer

Identifies and analyzes external system integrations from unified components,
data flows, and trust boundary information.
"""

from typing import Any, Dict, List

from fraim.config import Config

from .types import ComponentDiscoveryResults, ExternalIntegration, UnifiedComponent


class ExternalIntegrationAnalyzer:
    """Identifies external integrations from unified components and data flows."""

    def __init__(self, config: Config):
        self.config = config

    async def analyze_external_integrations(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Main entry point for external integration analysis using unified components."""
        try:
            external_integrations = []

            # Primary approach: Analyze external integrations from unified components and data flows
            if results.unified_components and results.unified_components.components:
                self.config.logger.info(
                    f"Analyzing external integrations for {len(results.unified_components.components)} unified components")

                # Get data flows and trust boundaries for context
                data_flows = results.data_flows or []
                trust_boundaries = results.trust_boundaries or []

                unified_externals = self._analyze_unified_component_external_integrations(
                    results.unified_components.components, data_flows, trust_boundaries
                )
                external_integrations.extend(unified_externals)
                self.config.logger.info(
                    f"Found {len(unified_externals)} external integrations from unified components")
            else:
                self.config.logger.warning(
                    "No unified components found, falling back to legacy fragmented analysis")

                # Fallback: Use legacy fragmented approach during transition
                if results.infrastructure:
                    infra_externals = self._extract_infrastructure_externals(
                        results.infrastructure)
                    external_integrations.extend(infra_externals)

                if results.api_interfaces:
                    api_externals = self._extract_api_externals(
                        results.api_interfaces)
                    external_integrations.extend(api_externals)

            # Deduplicate and categorize
            categorized_integrations = self._deduplicate_external_integrations(external_integrations)

            self.config.logger.info(f"Analyzed {len(categorized_integrations)} external integrations")
            return categorized_integrations

        except Exception as e:
            self.config.logger.error(f"External integration analysis failed: {str(e)}")
            return []

    def _analyze_unified_component_external_integrations(self, components: List[UnifiedComponent], data_flows: List[Dict[str, Any]], trust_boundaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze external integrations from unified components using data flows and trust boundaries."""
        external_integrations = []

        try:
            # Create component lookup
            component_map = {comp.component_id: comp for comp in components}

            # 1. Identify external integrations from data flows
            external_integrations.extend(
                self._extract_external_integrations_from_flows(data_flows, component_map))

            # 2. Identify external integrations from component infrastructure details
            for component in components:
                external_integrations.extend(
                    self._extract_external_integrations_from_component(component))

            # 3. Identify external integrations from API interfaces
            for component in components:
                external_integrations.extend(
                    self._extract_external_integrations_from_api_interfaces(component))

            # 4. Identify external integrations from trust boundary context
            external_integrations.extend(self._extract_external_integrations_from_trust_boundaries(
                trust_boundaries, component_map))

            self.config.logger.info(
                f"Extracted {len(external_integrations)} external integrations from unified components")
            return external_integrations

        except Exception as e:
            self.config.logger.error(
                f"Error analyzing unified component external integrations: {str(e)}")
            return []

    def _extract_external_integrations_from_flows(self, data_flows: List[Dict[str, Any]], component_map: Dict[str, UnifiedComponent]) -> List[Dict[str, Any]]:
        """Extract external integrations from data flows that cross system boundaries."""
        external_integrations = []

        for flow in data_flows:
            source = flow.get('source')
            target = flow.get('target')

            # Look for flows involving external sources/targets
            if source == 'external' or target == 'external':
                # Find the internal component in this flow
                internal_component_id = target if source == 'external' else source
                if internal_component_id and isinstance(internal_component_id, str):
                    internal_component = component_map.get(
                        internal_component_id)
                else:
                    internal_component = None

                if internal_component:
                    integration = {
                        "name": f"external_integration_via_{internal_component.component_name}",
                        "type": flow.get('type', 'unknown_external'),
                        "category": "data_flow_external",
                        "protocol": flow.get('protocol', 'unknown'),
                        "endpoint": None,  # External flows don't have specific endpoints
                        "authentication": flow.get('authentication', 'unknown'),
                        "data_classification": flow.get('data_classification', 'unknown'),
                        "criticality": self._assess_flow_criticality(flow),
                        "metadata": {
                            "flow_direction": "inbound" if source == 'external' else "outbound",
                            "internal_component": internal_component.component_name,
                            "internal_component_type": internal_component.component_type,
                            "port": flow.get('port'),
                            "encryption": flow.get('encryption', False),
                            "flow_type": flow.get('type'),
                        },
                    }
                    external_integrations.append(integration)

        return external_integrations

    def _extract_external_integrations_from_component(self, component: UnifiedComponent) -> List[Dict[str, Any]]:
        """Extract external integrations from component infrastructure details."""
        external_integrations = []

        # Check infrastructure details for external services
        if component.infrastructure_details:
            provider = component.infrastructure_details.get('provider')
            service_name = component.infrastructure_details.get('service_name')

            # Cloud provider services are external integrations
            if provider and provider.lower() in ['aws', 'azure', 'gcp', 'google']:
                integration = {
                    "name": f"{provider.lower()}_{component.component_name}",
                    "type": "cloud_service",
                    "category": "infrastructure_external",
                    "protocol": "HTTPS",
                    "endpoint": f"{provider.lower()}.com",
                    "authentication": "cloud_provider_auth",
                    "data_classification": self._classify_component_data_sensitivity(component),
                    "criticality": self._assess_component_criticality_for_external(component),
                    "metadata": {
                        "provider": provider,
                        "service_name": service_name,
                        "component_type": component.component_type,
                        "component_name": component.component_name,
                        "availability_zone": component.infrastructure_details.get('availability_zone'),
                        "configuration": component.infrastructure_details.get('configuration'),
                    },
                }
                external_integrations.append(integration)

        # Check deployment info for external dependencies (container registries, etc.)
        if component.deployment_info:
            base_image = component.deployment_info.get('base_image', '')
            if self._is_external_image(base_image):
                registry = self._extract_registry(base_image)
                if registry:
                    integration = {
                        "name": f"container_registry_{registry}",
                        "type": "container_registry",
                        "category": "infrastructure_external",
                        "protocol": "HTTPS",
                        "endpoint": registry,
                        "authentication": "registry_credentials",
                        "data_classification": "container_images",
                        "criticality": "high",  # Container images are critical for deployment
                        "metadata": {
                            "registry_type": self._classify_registry(registry),
                            "base_image": base_image,
                            "component_name": component.component_name,
                        },
                    }
                    external_integrations.append(integration)

        return external_integrations

    def _extract_external_integrations_from_api_interfaces(self, component: UnifiedComponent) -> List[Dict[str, Any]]:
        """Extract external integrations from component API interfaces."""
        external_integrations: List[Dict[str, Any]] = []

        if not component.api_interfaces:
            return external_integrations

        for api_interface in component.api_interfaces:
            api_type = api_interface.get('type', 'unknown')

            # Look for external API calls or third-party integrations
            if api_type == 'rest':
                endpoints = api_interface.get('endpoints', [])
                for endpoint in endpoints:
                    # Check for external API patterns
                    endpoint_path = endpoint.get('endpoint_path', '')
                    if self._indicates_external_api(endpoint_path):
                        integration = {
                            "name": f"external_api_{component.component_name}_{endpoint_path.replace('/', '_')}",
                            "type": "third_party_api",
                            "category": "api_external",
                            "protocol": "HTTPS" if endpoint.get('ssl_enabled', False) else "HTTP",
                            "endpoint": endpoint_path,
                            "authentication": endpoint.get('authentication', 'unknown'),
                            "data_classification": self._classify_endpoint_data_sensitivity(endpoint),
                            "criticality": "medium",
                            "metadata": {
                                "component_name": component.component_name,
                                "http_method": endpoint.get('http_method', 'GET'),
                                "endpoint_path": endpoint_path,
                                "api_type": api_type,
                            },
                        }
                        external_integrations.append(integration)

        return external_integrations

    def _extract_external_integrations_from_trust_boundaries(self, trust_boundaries: List[Dict[str, Any]], component_map: Dict[str, UnifiedComponent]) -> List[Dict[str, Any]]:
        """Extract external integrations from trust boundary analysis."""
        external_integrations = []

        for boundary in trust_boundaries:
            boundary_type = boundary.get('type')

            # DMZ and external boundaries indicate external integrations
            if boundary_type in ['dmz_boundary', 'external_boundary']:
                components = boundary.get('components', [])
                for component_name in components:
                    # Find component by name (need to match by name since boundary stores component names)
                    component = None
                    for comp in component_map.values():
                        if comp.component_name == component_name:
                            component = comp
                            break

                    if component:
                        integration = {
                            "name": f"external_boundary_integration_{component_name}",
                            "type": "boundary_external",
                            "category": "trust_boundary_external",
                            "protocol": "varies",
                            "endpoint": None,
                            "authentication": "varies",
                            "data_classification": "varies",
                            "criticality": boundary.get('threat_level', 'medium'),
                            "metadata": {
                                "boundary_name": boundary.get('name'),
                                "boundary_type": boundary_type,
                                "component_name": component_name,
                                "component_type": component.component_type,
                                "security_controls": boundary.get('security_controls', []),
                                "threat_level": boundary.get('threat_level'),
                            },
                        }
                        external_integrations.append(integration)

        return external_integrations

    def _assess_flow_criticality(self, flow: Dict[str, Any]) -> str:
        """Assess criticality of an external data flow."""
        data_classification = flow.get('data_classification', '').lower()

        if data_classification in ['sensitive', 'confidential']:
            return 'high'
        elif data_classification == 'internal':
            return 'medium'
        else:
            return 'low'

    def _classify_component_data_sensitivity(self, component: UnifiedComponent) -> str:
        """Classify data sensitivity for a component."""
        # Database components typically handle sensitive data
        if component.component_type == 'database':
            return 'sensitive'

        # Components with authentication mechanisms handle sensitive data
        if component.authentication_methods and any(auth in component.authentication_methods for auth in ['oauth', 'jwt', 'saml']):
            return 'sensitive'

        # API components handling user data
        if component.api_interfaces and any('user' in str(api).lower() or 'auth' in str(api).lower() for api in component.api_interfaces):
            return 'confidential'

        return 'internal'

    def _assess_component_criticality_for_external(self, component: UnifiedComponent) -> str:
        """Assess criticality of component for external integration purposes."""
        # Database and storage components are highly critical
        if component.component_type in ['database', 'storage']:
            return 'high'

        # Load balancers and gateways are critical for availability
        if component.component_type in ['load_balancer', 'gateway', 'proxy']:
            return 'high'

        # Services with external endpoints are medium criticality
        if component.endpoints:
            return 'medium'

        return 'low'

    def _indicates_external_api(self, endpoint_path: str) -> bool:
        """Check if endpoint path indicates external API integration."""
        external_indicators = [
            'webhook', 'callback', 'oauth', 'auth/external',
            'api/external', 'third-party', 'integration'
        ]

        path_lower = endpoint_path.lower()
        return any(indicator in path_lower for indicator in external_indicators)

    def _classify_endpoint_data_sensitivity(self, endpoint: Dict[str, Any]) -> str:
        """Classify data sensitivity for an API endpoint."""
        path = endpoint.get('endpoint_path', '').lower()
        method = endpoint.get('http_method', 'GET').upper()

        # Authentication endpoints handle sensitive data
        if any(term in path for term in ['auth', 'login', 'password', 'token']):
            return 'sensitive'

        # User data endpoints
        if any(term in path for term in ['user', 'profile', 'account']):
            return 'confidential'

        # Write operations typically handle more sensitive data
        if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return 'internal'

        return 'public'

    def _extract_infrastructure_externals(self, infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract external integrations from infrastructure."""
        externals = []

        try:
            # Extract external services from infrastructure components
            if "infrastructure_components" in infrastructure:
                components = infrastructure["infrastructure_components"]
                for component in components:
                    if isinstance(component, dict) and self._is_external_component(component):
                        external = {
                            "name": component.get("name", "unknown_external"),
                            "type": component.get("type", "infrastructure_service"),
                            "category": "infrastructure",
                            "protocol": "HTTPS",
                            "endpoint": component.get("endpoint"),
                            "authentication": "cloud_provider",
                            "data_classification": self._classify_component_data(component),
                            "criticality": self._assess_component_criticality(component),
                            "metadata": {
                                "provider": component.get("provider"),
                                "service_name": component.get("service_name"),
                                "environment": component.get("environment"),
                                "configuration": component.get("configuration", {}),
                            },
                        }
                        externals.append(external)

            # Extract external container registries and base images
            if "container_configs" in infrastructure:
                containers = infrastructure["container_configs"]
                registry_externals = set()  # Track unique registries

                for container in containers:
                    if isinstance(container, dict):
                        base_image = container.get("base_image", "")
                        if self._is_external_image(base_image):
                            # Extract registry from image name
                            registry = self._extract_registry(base_image)
                            if registry and registry not in registry_externals:
                                registry_externals.add(registry)
                                external = {
                                    "name": f"container_registry_{registry}",
                                    "type": "container_registry",
                                    "category": "infrastructure",
                                    "protocol": "HTTPS",
                                    "endpoint": registry,
                                    "authentication": "registry_auth",
                                    "data_classification": "container_images",
                                    "criticality": "high",
                                    "metadata": {
                                        "registry_type": self._classify_registry(registry),
                                        "images_used": [container.get("base_image")],
                                    },
                                }
                                externals.append(external)

            self.config.logger.info(f"Extracted {len(externals)} infrastructure external integrations")
            return externals

        except Exception as e:
            self.config.logger.error(f"Error extracting infrastructure externals: {str(e)}")
            return []

    def _extract_api_externals(self, api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract external integrations from API interfaces."""
        externals = []

        try:
            # Extract external API calls from REST endpoints
            if "rest_endpoints" in api_interfaces:
                endpoints = api_interfaces["rest_endpoints"]
                external_apis = set()  # Track unique external APIs

                for endpoint in endpoints:
                    if isinstance(endpoint, dict):
                        service_name = endpoint.get("service_name", "")
                        endpoint_path = endpoint.get("endpoint_path", "")

                        # Check if this looks like an external API call
                        if self._is_external_api_endpoint(endpoint):
                            api_key = f"{service_name}_{endpoint_path}"
                            if api_key not in external_apis:
                                external_apis.add(api_key)
                                external = {
                                    "name": service_name or "external_api",
                                    "type": "external_api",
                                    "category": "api",
                                    "protocol": "HTTPS",
                                    "endpoint": endpoint_path,
                                    "authentication": endpoint.get("auth_type", "api_key"),
                                    "data_classification": self._classify_api_data(endpoint),
                                    "criticality": self._assess_api_criticality(endpoint),
                                    "metadata": {
                                        "http_method": endpoint.get("http_method"),
                                        "service_name": service_name,
                                        "owasp_risks": endpoint.get("owasp_risks", []),
                                        "requires_auth": endpoint.get("requires_auth", False),
                                    },
                                }
                                externals.append(external)

            # Extract external services from existing data flows
            if "data_flows" in api_interfaces:
                flows = api_interfaces["data_flows"]
                for flow in flows:
                    if isinstance(flow, dict) and self._is_external_flow(flow):
                        external = {
                            "name": flow.get("destination", "external_service"),
                            "type": "external_data_flow",
                            "category": "api",
                            "protocol": "HTTPS",
                            "endpoint": flow.get("destination"),
                            "authentication": "unknown",
                            "data_classification": flow.get("data_format", "unknown"),
                            "criticality": "medium",
                            "metadata": {
                                "flow_name": flow.get("flow_name"),
                                "data_format": flow.get("data_format"),
                                "transformation_logic": flow.get("transformation_logic"),
                                "error_handling": flow.get("error_handling"),
                            },
                        }
                        externals.append(external)

            # Extract third-party libraries from vulnerabilities (if available)
            if "vulnerabilities" in api_interfaces:
                vulnerabilities = api_interfaces["vulnerabilities"]
                libraries = set()

                for vuln in vulnerabilities:
                    if isinstance(vuln, dict):
                        component = vuln.get("component", "")
                        if component and self._is_third_party_library(component):
                            if component not in libraries:
                                libraries.add(component)
                                external = {
                                    "name": component,
                                    "type": "third_party_library",
                                    "category": "api",
                                    "protocol": "package_manager",
                                    "endpoint": None,
                                    "authentication": "none",
                                    "data_classification": "code_dependency",
                                    "criticality": self._assess_library_criticality(vuln),
                                    "metadata": {
                                        "vulnerability_count": 1,
                                        "risk_level": vuln.get("risk_level"),
                                        "owasp_category": vuln.get("owasp_category"),
                                    },
                                }
                                externals.append(external)

            self.config.logger.info(f"Extracted {len(externals)} API external integrations")
            return externals

        except Exception as e:
            self.config.logger.error(f"Error extracting API externals: {str(e)}")
            return []

    def _deduplicate_external_integrations(self, integrations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate external integrations and categorize by risk."""
        try:
            # Create a set to track unique integrations
            unique_integrations = {}

            for integration in integrations:
                # Create a unique key for the integration
                integration_key = self._create_integration_key(integration)

                if integration_key not in unique_integrations:
                    # First time seeing this integration
                    unique_integrations[integration_key] = integration.copy()
                else:
                    # Merge with existing integration
                    existing = unique_integrations[integration_key]
                    merged = self._merge_integrations(existing, integration)
                    unique_integrations[integration_key] = merged

            # Enrich integrations with risk assessment
            enriched_integrations = []
            for integration in unique_integrations.values():
                enriched = self._enrich_integration(integration)
                enriched_integrations.append(enriched)

            # Sort by risk and criticality
            enriched_integrations.sort(
                key=lambda x: (
                    self._risk_priority(x.get("risk_level", "medium")),
                    self._criticality_priority(x.get("criticality", "medium")),
                ),
                reverse=True,
            )

            self.config.logger.info(f"Deduplicated to {len(enriched_integrations)} unique integrations")
            return enriched_integrations

        except Exception as e:
            self.config.logger.error(f"Error deduplicating integrations: {str(e)}")
            return integrations

    def _create_integration_key(self, integration: Dict[str, Any]) -> str:
        """Create a unique key for integration deduplication."""
        name = integration.get("name", "unknown")
        endpoint = integration.get("endpoint", "none")
        protocol = integration.get("protocol", "unknown")
        return f"{name}:{endpoint}:{protocol}"

    def _merge_integrations(self, int1: Dict[str, Any], int2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two integrations with the same key."""
        merged = int1.copy()

        # Merge metadata
        metadata1 = int1.get("metadata", {})
        metadata2 = int2.get("metadata", {})
        merged_metadata = {**metadata1, **metadata2}
        merged["metadata"] = merged_metadata

        # Use more specific authentication and classification
        if int2.get("authentication") != "unknown" and int1.get("authentication") == "unknown":
            merged["authentication"] = int2["authentication"]

        if int2.get("data_classification") != "unknown" and int1.get("data_classification") == "unknown":
            merged["data_classification"] = int2["data_classification"]

        # Use higher criticality
        if self._criticality_priority(int2.get("criticality", "medium")) > self._criticality_priority(
            int1.get("criticality", "medium")
        ):
            merged["criticality"] = int2["criticality"]

        return merged

    def _enrich_integration(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich integration with risk assessment and security analysis."""
        enriched = integration.copy()

        # Add risk assessment
        enriched["risk_level"] = self._assess_integration_risk(integration)

        # Add security posture
        enriched["security_posture"] = self._assess_security_posture(integration)

        # Add compliance considerations
        enriched["compliance_impact"] = self._assess_compliance_impact(integration)

        return enriched

    def _assess_integration_risk(self, integration: Dict[str, Any]) -> str:
        """Assess the risk level of an external integration."""
        risk_score = 0

        # Check data classification
        data_class = integration.get("data_classification", "unknown")
        if data_class in ["sensitive", "confidential", "persistent_data"]:
            risk_score += 2
        elif data_class == "unknown":
            risk_score += 1

        # Check authentication method
        auth = integration.get("authentication", "unknown")
        if auth in ["none", "unknown"]:
            risk_score += 3
        elif auth in ["basic", "api_key"]:
            risk_score += 1

        # Check protocol security
        protocol = integration.get("protocol", "unknown")
        if protocol in ["HTTP", "FTP", "TELNET"]:
            risk_score += 2

        # Check if it's a managed service (generally lower risk)
        if integration.get("type") in ["managed_database", "managed_storage"]:
            risk_score -= 1

        # Check criticality
        if integration.get("criticality") == "high":
            risk_score += 1

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    def _assess_security_posture(self, integration: Dict[str, Any]) -> str:
        """Assess the security posture of an integration."""
        protocol = integration.get("protocol", "unknown")
        auth = integration.get("authentication", "unknown")

        secure_protocols = ["HTTPS", "TLS", "SSL", "SFTP"]
        secure_auth = ["oauth", "saml", "certificate", "mutual_tls"]

        if protocol in secure_protocols and auth in secure_auth:
            return "excellent"
        elif protocol in secure_protocols or auth in secure_auth:
            return "good"
        elif auth not in ["none", "unknown"]:
            return "fair"
        else:
            return "poor"

    def _assess_compliance_impact(self, integration: Dict[str, Any]) -> str:
        """Assess compliance impact of an integration."""
        data_class = integration.get("data_classification", "unknown")

        if data_class in ["sensitive", "confidential", "persistent_data"]:
            return "high"
        elif integration.get("type") in ["managed_database", "external_api"]:
            return "medium"
        else:
            return "low"

    def _risk_priority(self, risk_level: str) -> int:
        """Convert risk level to numeric priority for sorting."""
        return {"high": 3, "medium": 2, "low": 1}.get(risk_level, 2)

    def _criticality_priority(self, criticality: str) -> int:
        """Convert criticality to numeric priority for sorting."""
        return {"high": 3, "medium": 2, "low": 1}.get(criticality, 2)

    # Helper methods for classification
    def _is_external_component(self, component: Dict[str, Any]) -> bool:
        """Check if an infrastructure component is external."""
        provider = component.get("provider", "").lower()
        service_name = component.get("service_name", "").lower()

        # Common cloud providers and external services
        external_providers = ["aws", "azure", "gcp", "cloudflare", "mongodb", "redis"]
        return any(provider in provider.lower() for provider in external_providers) or any(
            service in service_name for service in ["atlas", "cloud"]
        )

    def _is_external_image(self, image: str) -> bool:
        """Check if a container image is from an external registry."""
        if not image:
            return False

        # Images without registry prefix are from Docker Hub (external)
        if "/" not in image or image.count("/") == 1:
            return True

        # Common external registries
        external_registries = ["docker.io", "quay.io", "gcr.io", "registry.hub.docker.com"]
        return any(registry in image for registry in external_registries)

    def _extract_registry(self, image: str) -> str:
        """Extract registry name from image."""
        if not image:
            return ""

        if "/" not in image:
            return "docker.io"  # Default registry

        parts = image.split("/")
        if len(parts) >= 2 and "." in parts[0]:
            return parts[0]
        else:
            return "docker.io"  # Default for short names

    def _classify_registry(self, registry: str) -> str:
        """Classify the type of container registry."""
        if "docker.io" in registry:
            return "docker_hub"
        elif "gcr.io" in registry:
            return "google_container_registry"
        elif "quay.io" in registry:
            return "red_hat_quay"
        else:
            return "private_registry"

    def _is_external_api_endpoint(self, endpoint: Dict[str, Any]) -> bool:
        """Check if an API endpoint calls external services."""
        path = endpoint.get("endpoint_path", "").lower()
        service_name = endpoint.get("service_name", "").lower()

        # Look for indicators of external API calls
        external_indicators = ["api.", "service.", "webhook", "callback", "oauth", "payment"]
        return any(indicator in path or indicator in service_name for indicator in external_indicators)

    def _is_external_flow(self, flow: Dict[str, Any]) -> bool:
        """Check if a data flow goes to external services."""
        destination = flow.get("destination", "").lower()
        source = flow.get("source", "").lower()

        # Check for external destinations
        external_indicators = ["api", "service", "external", "third-party", "webhook"]
        return any(indicator in destination or indicator in source for indicator in external_indicators)

    def _is_third_party_library(self, component: str) -> bool:
        """Check if a component is a third-party library."""
        # Simple heuristic - most vulnerabilities in third-party libraries
        return len(component) > 3 and not component.startswith("internal")

    def _classify_component_data(self, component: Dict[str, Any]) -> str:
        """Classify data sensitivity for infrastructure components."""
        comp_type = component.get("type", "").lower()

        if comp_type in ["database", "storage", "cache"]:
            return "persistent_data"
        elif comp_type in ["load_balancer", "api_gateway"]:
            return "application_data"
        else:
            return "infrastructure_data"

    def _classify_api_data(self, endpoint: Dict[str, Any]) -> str:
        """Classify data sensitivity for API endpoints."""
        path = endpoint.get("endpoint_path", "").lower()

        if any(term in path for term in ["auth", "login", "password", "token"]):
            return "sensitive"
        elif endpoint.get("requires_auth", False):
            return "confidential"
        else:
            return "public"

    def _assess_component_criticality(self, component: Dict[str, Any]) -> str:
        """Assess criticality of infrastructure component."""
        comp_type = component.get("type", "").lower()

        if comp_type in ["database", "storage"]:
            return "high"
        elif comp_type in ["load_balancer", "api_gateway"]:
            return "high"
        else:
            return "medium"

    def _assess_api_criticality(self, endpoint: Dict[str, Any]) -> str:
        """Assess criticality of API endpoint."""
        owasp_risks = endpoint.get("owasp_risks", [])

        if any(risk.get("risk_level") == "high" for risk in owasp_risks if isinstance(risk, dict)):
            return "high"
        elif endpoint.get("requires_auth", False):
            return "medium"
        else:
            return "low"

    def _assess_library_criticality(self, vuln: Dict[str, Any]) -> str:
        """Assess criticality based on vulnerability."""
        risk_level = vuln.get("risk_level", "").lower()

        if risk_level in ["high", "critical"]:
            return "high"
        elif risk_level == "medium":
            return "medium"
        else:
            return "low"
