# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Trust Boundary Analyzer

Analyzes and groups unified system components into trust boundaries based on
data flows, security levels, and component relationships.
"""

from typing import Any, Dict, List, Tuple

from fraim.config import Config

from .types import ComponentDiscoveryResults, TrustBoundary, UnifiedComponent


class TrustBoundaryAnalyzer:
    """Groups unified components into trust boundaries based on data flows and security levels."""

    def __init__(self, config: Config):
        self.config = config

    async def analyze_trust_boundaries(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Main entry point for trust boundary analysis using unified components."""
        try:
            self.config.logger.info("Starting trust boundary analysis")
            trust_boundaries = []

            # Primary approach: Analyze trust boundaries from unified components and data flows
            if results.unified_components and results.unified_components.components:
                self.config.logger.info(
                    f"Analyzing trust boundaries for {len(results.unified_components.components)} unified components")

                # Get data flows if available for relationship analysis
                data_flows = results.data_flows or []

                unified_boundaries = self._analyze_unified_component_trust_boundaries(
                    results.unified_components.components, data_flows
                )
                trust_boundaries.extend(unified_boundaries)
                self.config.logger.info(
                    f"Found {len(unified_boundaries)} unified trust boundaries")
            else:
                self.config.logger.warning(
                    "No unified components found, falling back to legacy fragmented analysis")

                # Fallback: Use legacy fragmented approach during transition
                if results.infrastructure:
                    self.config.logger.info(
                        "Processing infrastructure trust boundaries")
                    network_boundaries = self._identify_network_trust_boundaries(
                        results.infrastructure)
                    trust_boundaries.extend(network_boundaries)
                    self.config.logger.info(
                        f"Found {len(network_boundaries)} infrastructure trust boundaries")

                if results.api_interfaces:
                    self.config.logger.info("Processing API trust boundaries")
                    api_boundaries = self._identify_api_trust_boundaries(
                        results.api_interfaces)
                    trust_boundaries.extend(api_boundaries)
                    self.config.logger.info(
                        f"Found {len(api_boundaries)} API trust boundaries")

            # Analyze and prioritize boundaries
            analyzed_boundaries = self._analyze_trust_boundaries(trust_boundaries)

            self.config.logger.info(f"Analyzed {len(analyzed_boundaries)} trust boundaries")
            return analyzed_boundaries

        except Exception as e:
            self.config.logger.error(f"Trust boundary analysis failed: {str(e)}")
            import traceback

            self.config.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _analyze_unified_component_trust_boundaries(self, components: List[UnifiedComponent], data_flows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze trust boundaries from unified components and data flows."""
        boundaries = []

        try:
            # Create component mapping for quick lookup
            component_map = {comp.component_id: comp for comp in components}

            # Group components into trust zones based on multiple criteria
            trust_zones = self._group_components_into_trust_zones(
                components, data_flows, component_map)

            # Convert trust zones into trust boundary objects
            for zone_name, zone_info in trust_zones.items():
                boundary = self._create_trust_boundary_from_zone(
                    zone_name, zone_info, data_flows)
                boundaries.append(boundary)

            # Add inter-zone boundaries (boundaries between trust zones)
            inter_zone_boundaries = self._identify_inter_zone_boundaries(
                trust_zones, data_flows, component_map)
            boundaries.extend(inter_zone_boundaries)

            self.config.logger.info(
                f"Created {len(boundaries)} trust boundaries from unified components")
            return boundaries

        except Exception as e:
            self.config.logger.error(
                f"Error analyzing unified component trust boundaries: {str(e)}")
            return []

    def _group_components_into_trust_zones(self, components: List[UnifiedComponent], data_flows: List[Dict[str, Any]], component_map: Dict[str, UnifiedComponent]) -> Dict[str, Dict[str, Any]]:
        """Group components into trust zones based on security levels, exposure, and data flows."""
        trust_zones: Dict[str, Dict[str, Any]] = {}

        for component in components:
            # Determine trust zone based on component characteristics
            zone_name = self._determine_component_trust_zone(
                component, data_flows)

            if zone_name not in trust_zones:
                trust_zones[zone_name] = {
                    'components': [],
                    'component_types': set(),
                    'security_level': 'medium',
                    'external_exposure': False,
                    'data_classifications': set(),
                    'protocols': set(),
                }

            # Add component to trust zone
            trust_zones[zone_name]['components'].append(component)
            trust_zones[zone_name]['component_types'].add(
                component.component_type)
            trust_zones[zone_name]['protocols'].update(component.protocols)

            # Update zone characteristics based on component
            if self._is_externally_exposed(component, data_flows):
                trust_zones[zone_name]['external_exposure'] = True

            # Update security level based on component sensitivity
            component_security = self._assess_component_security_level(
                component)
            current_security = trust_zones[zone_name]['security_level']
            trust_zones[zone_name]['security_level'] = self._merge_security_levels(
                current_security, component_security)

            # Collect data classifications from flows involving this component
            component_data_classes = self._get_component_data_classifications(
                component, data_flows)
            trust_zones[zone_name]['data_classifications'].update(
                component_data_classes)

        return trust_zones

    def _determine_component_trust_zone(self, component: UnifiedComponent, data_flows: List[Dict[str, Any]]) -> str:
        """Determine which trust zone a component belongs to."""

        # DMZ zone for externally exposed components
        if self._is_externally_exposed(component, data_flows):
            if component.component_type == 'load_balancer':
                return 'external_dmz'
            elif component.component_type == 'service' and component.api_interfaces:
                return 'api_dmz'
            else:
                return 'public_zone'

        # Data zone for databases and storage
        elif component.component_type in ['database', 'storage', 'cache']:
            sensitivity = self._assess_component_security_level(component)
            if sensitivity == 'high':
                return 'sensitive_data_zone'
            else:
                return 'data_zone'

        # Internal service zone
        elif component.component_type == 'service':
            return 'internal_service_zone'

        # Infrastructure zone for queues, proxies, etc.
        elif component.component_type in ['queue', 'proxy', 'gateway', 'cdn']:
            return 'infrastructure_zone'

        # Default internal zone
        else:
            return 'internal_zone'

    def _is_externally_exposed(self, component: UnifiedComponent, data_flows: List[Dict[str, Any]]) -> bool:
        """Check if component is exposed to external networks."""

        # Check if component has public endpoints
        if component.endpoints:
            return True

        # Check if component has flows from/to external sources
        for flow in data_flows:
            if ((flow.get('source') == 'external' and flow.get('target') == component.component_id) or
                    (flow.get('target') == 'external' and flow.get('source') == component.component_id)):
                return True

        # Check for common external exposure ports
        external_ports = {80, 443, 8080, 8443}
        if any(port in external_ports for port in component.exposed_ports):
            return True

        return False

    def _assess_component_security_level(self, component: UnifiedComponent) -> str:
        """Assess the security sensitivity level of a component."""

        # Database components are typically high security
        if component.component_type == 'database':
            return 'high'

        # Components with authentication/authorization are high security
        if any(auth in component.authentication_methods for auth in ['oauth', 'jwt', 'saml']):
            return 'high'

        # Components handling sensitive data paths
        sensitive_indicators = ['auth', 'admin', 'payment', 'user', 'account']
        if any(indicator in component.component_name.lower() for indicator in sensitive_indicators):
            return 'high'

        # API services are medium security by default
        if component.component_type == 'service' and component.api_interfaces:
            return 'medium'

        # Infrastructure components are typically low-medium
        if component.component_type in ['load_balancer', 'proxy', 'cdn']:
            return 'low'

        return 'medium'

    def _get_component_data_classifications(self, component: UnifiedComponent, data_flows: List[Dict[str, Any]]) -> set:
        """Get data classifications for flows involving this component."""
        classifications = set()

        for flow in data_flows:
            if flow.get('source') == component.component_id or flow.get('target') == component.component_id:
                data_class = flow.get('data_classification')
                if data_class:
                    classifications.add(data_class)

        return classifications

    def _merge_security_levels(self, current: str, new: str) -> str:
        """Merge security levels, taking the higher security level."""
        levels = {'low': 1, 'medium': 2, 'high': 3}
        current_level = levels.get(current, 2)
        new_level = levels.get(new, 2)

        if new_level > current_level:
            return new
        return current

    def _create_trust_boundary_from_zone(self, zone_name: str, zone_info: Dict[str, Any], data_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a trust boundary object from a trust zone."""

        components = zone_info['components']
        component_names = [comp.component_name for comp in components]
        component_ids = [comp.component_id for comp in components]

        # Determine security controls based on zone characteristics
        security_controls = self._determine_zone_security_controls(
            zone_name, zone_info)

        # Determine threat level based on exposure and data sensitivity
        threat_level = self._assess_zone_threat_level(zone_name, zone_info)

        # Create description
        description = self._create_zone_description(zone_name, zone_info)

        boundary = {
            "name": zone_name,
            "type": self._map_zone_to_boundary_type(zone_name),
            "category": "unified_component_grouping",
            "components": component_names,
            "security_controls": security_controls,
            "threat_level": threat_level,
            "description": description,
            "metadata": {
                "component_count": len(components),
                "component_types": list(zone_info['component_types']),
                "component_ids": component_ids,
                "external_exposure": zone_info['external_exposure'],
                "security_level": zone_info['security_level'],
                "data_classifications": list(zone_info['data_classifications']),
                "protocols": list(zone_info['protocols']),
            },
        }

        return boundary

    def _determine_zone_security_controls(self, zone_name: str, zone_info: Dict[str, Any]) -> List[str]:
        """Determine appropriate security controls for a trust zone."""
        controls = []

        # Base controls for all zones
        controls.append("Access Control")
        controls.append("Logging and Monitoring")

        # External exposure controls
        if zone_info['external_exposure']:
            controls.extend([
                "Web Application Firewall",
                "DDoS Protection",
                "Rate Limiting",
                "Input Validation"
            ])

        # Data protection controls
        if 'sensitive' in zone_info['data_classifications'] or 'confidential' in zone_info['data_classifications']:
            controls.extend([
                "Data Encryption",
                "Data Loss Prevention",
                "Backup and Recovery",
                "Data Classification"
            ])

        # Database specific controls
        if 'database' in zone_info['component_types']:
            controls.extend([
                "Database Security",
                "Query Monitoring",
                "Privilege Management",
                "Data Masking"
            ])

        # API specific controls
        if any(comp.api_interfaces for comp in zone_info['components']):
            controls.extend([
                "API Security",
                "Authentication",
                "Authorization",
                "API Rate Limiting"
            ])

        return list(set(controls))  # Remove duplicates

    def _assess_zone_threat_level(self, zone_name: str, zone_info: Dict[str, Any]) -> str:
        """Assess threat level for a trust zone."""

        # External exposure increases threat level
        if zone_info['external_exposure']:
            return 'high'

        # Sensitive data increases threat level
        if zone_info['security_level'] == 'high':
            return 'high'

        # Database zones are typically high threat
        if 'database' in zone_info['component_types']:
            return 'high'

        # DMZ zones are high threat
        if 'dmz' in zone_name.lower():
            return 'high'

        return 'medium'

    def _create_zone_description(self, zone_name: str, zone_info: Dict[str, Any]) -> str:
        """Create a descriptive text for the trust zone."""
        component_count = len(zone_info['components'])
        component_types = list(zone_info['component_types'])

        description = f"Trust boundary containing {component_count} component(s) of types: {', '.join(component_types)}."

        if zone_info['external_exposure']:
            description += " This zone is externally exposed and requires enhanced security controls."

        if zone_info['security_level'] == 'high':
            description += " Contains sensitive components requiring strict access controls."

        return description

    def _map_zone_to_boundary_type(self, zone_name: str) -> str:
        """Map trust zone names to boundary types."""
        zone_mappings = {
            'external_dmz': 'dmz_boundary',
            'api_dmz': 'dmz_boundary',
            'public_zone': 'external_boundary',
            'sensitive_data_zone': 'data_boundary',
            'data_zone': 'data_boundary',
            'internal_service_zone': 'application_boundary',
            'infrastructure_zone': 'network_boundary',
            'internal_zone': 'internal_boundary'
        }

        return zone_mappings.get(zone_name, 'trust_boundary')

    def _identify_inter_zone_boundaries(self, trust_zones: Dict[str, Dict[str, Any]], data_flows: List[Dict[str, Any]], component_map: Dict[str, UnifiedComponent]) -> List[Dict[str, Any]]:
        """Identify boundaries between trust zones based on data flows."""
        inter_zone_boundaries = []

        # Create zone lookup for components
        component_to_zone = {}
        for zone_name, zone_info in trust_zones.items():
            for component in zone_info['components']:
                component_to_zone[component.component_id] = zone_name

        # Analyze flows between different zones
        zone_connections: Dict[str, Dict[str, Any]] = {}
        for flow in data_flows:
            source_id = flow.get('source')
            target_id = flow.get('target')

            # Skip external flows for now
            if source_id in ['external', 'client'] or target_id in ['external', 'client']:
                continue

            source_zone = component_to_zone.get(source_id)
            target_zone = component_to_zone.get(target_id)

            if source_zone and target_zone and source_zone != target_zone:
                sorted_zones = sorted([source_zone, target_zone])
                connection_key = f"{sorted_zones[0]}__{sorted_zones[1]}"

                if connection_key not in zone_connections:
                    zone_connections[connection_key] = {
                        'flows': [],
                        'data_classifications': set(),
                        'protocols': set()
                    }

                zone_connections[connection_key]['flows'].append(flow)
                zone_connections[connection_key]['data_classifications'].add(
                    flow.get('data_classification', 'unknown'))
                zone_connections[connection_key]['protocols'].add(
                    flow.get('protocol', 'unknown'))

        # Create inter-zone boundary objects
        for connection_key, connection_info in zone_connections.items():
            zone1, zone2 = connection_key.split("__")
            boundary = {
                "name": f"InterZone_{zone1}_to_{zone2}",
                "type": "inter_zone_boundary",
                "category": "zone_crossing",
                "components": [zone1, zone2],
                "security_controls": [
                    "Zone Crossing Controls",
                    "Traffic Inspection",
                    "Access Policy Enforcement"
                ],
                "threat_level": self._assess_inter_zone_threat_level(zone1, zone2, connection_info),
                "description": f"Boundary controlling data flows between {zone1} and {zone2} zones",
                "metadata": {
                    "flow_count": len(connection_info['flows']),
                    "data_classifications": list(connection_info['data_classifications']),
                    "protocols": list(connection_info['protocols']),
                    "source_zone": zone1,
                    "target_zone": zone2,
                },
            }
            inter_zone_boundaries.append(boundary)

        return inter_zone_boundaries

    def _assess_inter_zone_threat_level(self, zone1: str, zone2: str, connection_info: Dict[str, Any]) -> str:
        """Assess threat level for inter-zone boundaries."""

        # Connections involving DMZ zones are high risk
        if 'dmz' in zone1.lower() or 'dmz' in zone2.lower():
            return 'high'

        # Connections involving sensitive data zones are high risk
        if 'sensitive' in zone1.lower() or 'sensitive' in zone2.lower():
            return 'high'

        # Multiple data classifications suggest complex flows = higher risk
        if len(connection_info['data_classifications']) > 2:
            return 'high'

        return 'medium'

    def _identify_network_trust_boundaries(self, infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify network-level trust boundaries."""
        boundaries = []

        try:
            # Handle actual structure returned by infrastructure discovery
            # Check for infrastructure components (databases, load balancers, etc.)
            if "infrastructure_components" in infrastructure:
                components = infrastructure["infrastructure_components"]

                # Create boundaries for database components
                for component in components:
                    if isinstance(component, dict) and component.get("type") == "database":
                        boundary = {
                            "name": f"Database_{component.get('name', 'unknown')}",
                            "type": "data_boundary",
                            "category": "infrastructure",
                            "components": [component.get("name", "unknown")],
                            "security_controls": ["Database Security"],
                            "threat_level": "high",
                            "description": f"Database boundary protecting {component.get('service_name', 'data')}",
                            "metadata": {
                                "provider": component.get("provider"),
                                "service_name": component.get("service_name"),
                            },
                        }
                        boundaries.append(boundary)

                    elif isinstance(component, dict) and component.get("type") == "load_balancer":
                        boundary = {
                            "name": f"LoadBalancer_{component.get('name', 'unknown')}",
                            "type": "dmz_boundary",
                            "category": "infrastructure",
                            "components": [component.get("name", "unknown")],
                            "security_controls": ["Load Balancer Security"],
                            "threat_level": "high",
                            "description": f"Load balancer boundary exposing internal services",
                            "metadata": {
                                "provider": component.get("provider"),
                                "service_name": component.get("service_name"),
                            },
                        }
                        boundaries.append(boundary)

            # Identify DMZ boundaries from deployment topology
            if "deployment_topology" in infrastructure:
                topology = infrastructure["deployment_topology"]

                # Load balancer boundaries (often DMZ)
                if "load_balancers" in topology:
                    load_balancers = topology["load_balancers"]
                    for lb in load_balancers:
                        if isinstance(lb, dict) and lb.get("external", False):
                            boundary = {
                                "name": f"DMZ_LoadBalancer_{lb.get('name', 'unknown')}",
                                "type": "dmz_boundary",
                                "category": "infrastructure",
                                "components": [lb.get("name", "unknown")] + lb.get("target_group", []),
                                "security_controls": self._get_load_balancer_security_controls(lb),
                                "threat_level": "high",  # DMZ is high risk
                                "description": f"DMZ boundary at load balancer exposing internal services",
                                "metadata": {
                                    "load_balancer_type": lb.get("type"),
                                    "ssl_termination": lb.get("ssl_enabled", False),
                                    "health_checks": lb.get("health_check", {}),
                                    "target_count": len(lb.get("target_group", [])),
                                },
                            }
                            boundaries.append(boundary)

                # Database boundaries
                if "databases" in topology:
                    databases = topology["databases"]
                    for db in databases:
                        if isinstance(db, dict):
                            boundary = {
                                "name": f"Database_{db.get('name', 'unknown')}",
                                "type": "data_boundary",
                                "category": "infrastructure",
                                "components": [db.get("name", "unknown")],
                                "security_controls": self._get_database_security_controls(db),
                                "threat_level": "high",  # Databases are high value targets
                                "description": f"Database boundary protecting persistent data",
                                "metadata": {
                                    "engine": db.get("engine"),
                                    "encrypted": db.get("encrypted", False),
                                    "backup_enabled": db.get("backup_enabled", False),
                                    "multi_az": db.get("multi_az", False),
                                    "publicly_accessible": db.get("publicly_accessible", False),
                                },
                            }
                            boundaries.append(boundary)

            self.config.logger.info(f"Identified {len(boundaries)} network trust boundaries")
            return boundaries

        except Exception as e:
            self.config.logger.error(f"Error identifying network trust boundaries: {str(e)}")
            return []

    def _identify_api_trust_boundaries(self, api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify API-level trust boundaries."""
        boundaries = []

        try:
            # Handle actual structure returned by API interface discovery
            # REST endpoint boundaries
            if "rest_endpoints" in api_interfaces:
                endpoints = api_interfaces["rest_endpoints"]

                # Group endpoints by service/gateway
                service_groups: Dict[str, List[Dict[str, Any]]] = {}
                for endpoint in endpoints:
                    if isinstance(endpoint, dict):
                        service = endpoint.get("handler_function", "unknown_service")
                        if service not in service_groups:
                            service_groups[service] = []
                        service_groups[service].append(endpoint)

                # Create boundaries for each service
                for service, service_endpoints in service_groups.items():
                    paths = [ep.get("endpoint_path", "unknown") for ep in service_endpoints]
                    methods = list(set(ep.get("http_method", "GET") for ep in service_endpoints))

                    boundary = {
                        "name": f"RestService_{service}",
                        "type": "api_service_boundary",
                        "category": "api",
                        "components": paths,
                        "security_controls": ["REST API Security"],
                        "threat_level": "high"
                        if any(ep.get("endpoint_path", "").startswith("/admin") for ep in service_endpoints)
                        else "medium",
                        "description": f"REST API service boundary for {service}",
                        "metadata": {
                            "service_name": service,
                            "endpoint_count": len(service_endpoints),
                            "http_methods": methods,
                            "rate_limiting": any(ep.get("rate_limiting") for ep in service_endpoints),
                        },
                    }
                    boundaries.append(boundary)

            # Service mesh boundaries
            if "inter_service_communication" in api_interfaces:
                communications = api_interfaces["inter_service_communication"]

                # Identify service clusters
                services = set()
                for comm in communications:
                    if isinstance(comm, dict):
                        services.add(comm.get("source_service", "unknown"))
                        services.add(comm.get("target_service", "unknown"))

                # Create service mesh boundary
                if len(services) > 1:
                    boundary = {
                        "name": "ServiceMesh_Internal",
                        "type": "service_mesh",
                        "category": "api",
                        "components": list(services),
                        "security_controls": self._get_service_mesh_controls(communications),
                        "threat_level": "medium",
                        "description": f"Service mesh boundary for internal communication",
                        "metadata": {
                            "service_count": len(services),
                            "communication_patterns": len(communications),
                            "encrypted_channels": sum(1 for c in communications if c.get("encryption", False)),
                            "authentication_enabled": sum(
                                1 for c in communications if c.get("authentication") != "none"
                            ),
                        },
                    }
                    boundaries.append(boundary)

            # External API boundaries
            if "external_api_dependencies" in api_interfaces:
                dependencies = api_interfaces["external_api_dependencies"]
                for dep in dependencies:
                    if isinstance(dep, dict):
                        boundary = {
                            "name": f"ExternalAPI_{dep.get('name', 'unknown')}",
                            "type": "external_api_boundary",
                            "category": "api",
                            "components": [dep.get("name", "unknown")],
                            "security_controls": [dep.get("authentication", "unknown")],
                            "threat_level": self._assess_external_api_threat_level(dep),
                            "description": f"External API boundary for {dep.get('name', 'unknown')}",
                            "metadata": {
                                "provider": dep.get("provider"),
                                "data_classification": dep.get("data_classification", "unknown"),
                                "rate_limited": dep.get("rate_limit") is not None,
                                "sla": dep.get("sla"),
                            },
                        }
                        boundaries.append(boundary)

            # Authentication boundaries
            auth_boundaries = self._identify_authentication_boundaries(api_interfaces)
            boundaries.extend(auth_boundaries)

            self.config.logger.info(f"Identified {len(boundaries)} API trust boundaries")
            return boundaries

        except Exception as e:
            self.config.logger.error(f"Error identifying API trust boundaries: {str(e)}")
            return []

    def _analyze_trust_boundaries(self, boundaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze and prioritize trust boundaries."""
        try:
            analyzed_boundaries = []

            for boundary in boundaries:
                analyzed = boundary.copy()

                # Add risk assessment
                analyzed["risk_score"] = self._calculate_risk_score(boundary)

                # Add priority level
                analyzed["priority"] = self._determine_priority(boundary)

                # Add recommended controls
                analyzed["recommended_controls"] = self._recommend_security_controls(boundary)

                # Add threat vectors
                analyzed["threat_vectors"] = self._identify_threat_vectors(boundary)

                analyzed_boundaries.append(analyzed)

            # Sort by risk score and priority
            analyzed_boundaries.sort(
                key=lambda x: (x.get("risk_score", 0), self._priority_weight(x.get("priority", "medium"))), reverse=True
            )

            self.config.logger.info(f"Analyzed and prioritized {len(analyzed_boundaries)} trust boundaries")
            return analyzed_boundaries

        except Exception as e:
            self.config.logger.error(f"Error analyzing trust boundaries: {str(e)}")
            return boundaries

    def _calculate_risk_score(self, boundary: Dict[str, Any]) -> int:
        """Calculate risk score for a trust boundary."""
        score = 0

        # Base score by threat level
        threat_level = boundary.get("threat_level", "medium")
        if threat_level == "high":
            score += 5
        elif threat_level == "medium":
            score += 3
        else:
            score += 1

        # Increase score for public/external boundaries
        boundary_type = boundary.get("type", "")
        if "public" in boundary_type or "external" in boundary_type or "dmz" in boundary_type:
            score += 3

        # Consider security controls
        controls = boundary.get("security_controls", [])
        if len(controls) == 0:
            score += 2
        elif "none" in controls or "unknown" in controls:
            score += 1

        # Consider component count
        components = boundary.get("components", [])
        if len(components) > 5:
            score += 1

        return score

    def _determine_priority(self, boundary: Dict[str, Any]) -> str:
        """Determine priority level for a trust boundary."""
        risk_score = self._calculate_risk_score(boundary)

        if risk_score >= 8:
            return "critical"
        elif risk_score >= 6:
            return "high"
        elif risk_score >= 4:
            return "medium"
        else:
            return "low"

    def _recommend_security_controls(self, boundary: Dict[str, Any]) -> List[str]:
        """Recommend security controls for a trust boundary."""
        recommendations = []
        boundary_type = boundary.get("type", "")

        if "public" in boundary_type or "dmz" in boundary_type:
            recommendations.extend(
                [
                    "Web Application Firewall (WAF)",
                    "DDoS Protection",
                    "Rate Limiting",
                    "SSL/TLS Termination",
                    "Input Validation",
                ]
            )

        if "api" in boundary_type:
            recommendations.extend(
                [
                    "API Authentication",
                    "Rate Limiting",
                    "Request/Response Validation",
                    "API Gateway Logging",
                    "Circuit Breaker Pattern",
                ]
            )

        if "data" in boundary_type:
            recommendations.extend(
                [
                    "Database Encryption",
                    "Access Control Lists",
                    "Database Activity Monitoring",
                    "Backup Encryption",
                    "Network Isolation",
                ]
            )

        if "network" in boundary_type:
            recommendations.extend(
                ["Security Groups", "Network ACLs", "VPC Flow Logs", "Network Segmentation", "Intrusion Detection"]
            )

        return recommendations

    def _identify_threat_vectors(self, boundary: Dict[str, Any]) -> List[str]:
        """Identify potential threat vectors for a trust boundary."""
        threats = []
        boundary_type = boundary.get("type", "")

        if "public" in boundary_type or "external" in boundary_type:
            threats.extend(
                [
                    "External Attackers",
                    "DDoS Attacks",
                    "Web Application Attacks",
                    "Data Exfiltration",
                    "Man-in-the-Middle",
                ]
            )

        if "api" in boundary_type:
            threats.extend(
                ["API Abuse", "Injection Attacks", "Broken Authentication", "Rate Limit Bypass", "Data Exposure"]
            )

        if "data" in boundary_type:
            threats.extend(
                ["Data Breaches", "SQL Injection", "Privilege Escalation", "Backup Theft", "Insider Threats"]
            )

        return threats

    def _priority_weight(self, priority: str) -> int:
        """Convert priority to numeric weight for sorting."""
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(priority, 2)

    # Helper methods for component and control extraction
    def _get_vpc_components(self, vpc: Dict[str, Any], infrastructure: Dict[str, Any]) -> List[str]:
        """Get components within a VPC."""
        components = []
        vpc_id = vpc.get("id")

        # Add subnets
        if "network_architecture" in infrastructure and "subnets" in infrastructure["network_architecture"]:
            subnets = infrastructure["network_architecture"]["subnets"]
            for subnet in subnets:
                if isinstance(subnet, dict) and subnet.get("vpc_id") == vpc_id:
                    components.append(subnet.get("name", subnet.get("id", "unknown_subnet")))

        return components

    def _get_vpc_security_controls(self, vpc: Dict[str, Any]) -> List[str]:
        """Get security controls for a VPC."""
        controls = []

        if vpc.get("flow_logs", False):
            controls.append("VPC Flow Logs")
        if vpc.get("nat_gateways"):
            controls.append("NAT Gateways")
        if vpc.get("internet_gateway", False):
            controls.append("Internet Gateway")
        if vpc.get("vpn_gateway", False):
            controls.append("VPN Gateway")

        return controls

    def _get_subnet_components(self, subnet: Dict[str, Any], infrastructure: Dict[str, Any]) -> List[str]:
        """Get components within a subnet."""
        components = []
        subnet_id = subnet.get("id")

        # Find instances in this subnet
        if "deployment_topology" in infrastructure:
            topology = infrastructure["deployment_topology"]
            if "compute_instances" in topology:
                for instance in topology["compute_instances"]:
                    if isinstance(instance, dict) and instance.get("subnet_id") == subnet_id:
                        components.append(instance.get("name", instance.get("id", "unknown_instance")))

        return components

    def _get_subnet_security_controls(self, subnet: Dict[str, Any]) -> List[str]:
        """Get security controls for a subnet."""
        controls = []

        if subnet.get("security_group"):
            controls.append(f"Security Group: {subnet['security_group']}")
        if subnet.get("network_acl"):
            controls.append(f"Network ACL: {subnet['network_acl']}")
        if subnet.get("route_table"):
            controls.append("Custom Route Table")

        return controls

    def _get_security_group_components(self, sg: Dict[str, Any], infrastructure: Dict[str, Any]) -> List[str]:
        """Get components protected by a security group."""
        instances = sg.get("attached_instances", [])
        return [str(instance) for instance in instances] if instances else []

    def _get_security_group_controls(self, sg: Dict[str, Any]) -> List[str]:
        """Get security controls defined in a security group."""
        controls = []

        ingress_rules = sg.get("ingress_rules", [])
        egress_rules = sg.get("egress_rules", [])

        controls.append(f"Ingress Rules: {len(ingress_rules)}")
        controls.append(f"Egress Rules: {len(egress_rules)}")

        # Analyze rule types
        for rule in ingress_rules:
            if isinstance(rule, dict):
                protocol = rule.get("protocol", "unknown")
                port = rule.get("port", "unknown")
                controls.append(f"Allow {protocol}:{port}")

        return controls

    def _get_load_balancer_security_controls(self, lb: Dict[str, Any]) -> List[str]:
        """Get security controls for a load balancer."""
        controls = []

        if lb.get("ssl_enabled", False):
            controls.append("SSL/TLS Termination")
        if lb.get("waf_enabled", False):
            controls.append("Web Application Firewall")
        if lb.get("health_check"):
            controls.append("Health Checks")
        if lb.get("access_logs", False):
            controls.append("Access Logging")

        return controls

    def _get_database_security_controls(self, db: Dict[str, Any]) -> List[str]:
        """Get security controls for a database."""
        controls = []

        if db.get("encrypted", False):
            controls.append("Encryption at Rest")
        if db.get("backup_enabled", False):
            controls.append("Automated Backups")
        if not db.get("publicly_accessible", True):
            controls.append("Private Access Only")
        if db.get("multi_az", False):
            controls.append("Multi-AZ Deployment")
        if db.get("monitoring", False):
            controls.append("Performance Monitoring")

        return controls

    def _get_service_mesh_controls(self, communications: List[Dict[str, Any]]) -> List[str]:
        """Get security controls for service mesh."""
        controls = []

        if any(c.get("encryption", False) for c in communications):
            controls.append("mTLS Encryption")
        if any(c.get("authentication") != "none" for c in communications):
            controls.append("Service Authentication")
        if any(c.get("authorization") for c in communications):
            controls.append("Service Authorization")

        return controls

    def _identify_authentication_boundaries(self, api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify authentication boundaries in API interfaces."""
        boundaries = []

        # Group endpoints by authentication method
        if "api_endpoints" in api_interfaces:
            auth_groups: Dict[str, List[Dict[str, Any]]] = {}
            endpoints = api_interfaces["api_endpoints"]

            for endpoint in endpoints:
                if isinstance(endpoint, dict):
                    auth_method = endpoint.get("authentication", "none")
                    if auth_method not in auth_groups:
                        auth_groups[auth_method] = []
                    auth_groups[auth_method].append(endpoint)

            # Create boundaries for each auth method
            for auth_method, auth_endpoints in auth_groups.items():
                if auth_method != "none":
                    boundary = {
                        "name": f"AuthBoundary_{auth_method}",
                        "type": "authentication_boundary",
                        "category": "api",
                        "components": [ep.get("path", "unknown") for ep in auth_endpoints],
                        "security_controls": [auth_method],
                        "threat_level": "high" if auth_method in ["none", "basic"] else "medium",
                        "description": f"Authentication boundary using {auth_method}",
                        "metadata": {
                            "authentication_method": auth_method,
                            "endpoint_count": len(auth_endpoints),
                            "public_endpoints": sum(1 for ep in auth_endpoints if ep.get("public", False)),
                        },
                    }
                    boundaries.append(boundary)

        return boundaries

    # Threat level assessment helpers
    def _assess_network_threat_level(self, vpc: Dict[str, Any]) -> str:
        """Assess threat level for a VPC."""
        if vpc.get("internet_gateway", False) and len(vpc.get("public_subnets", [])) > 0:
            return "high"
        elif vpc.get("vpn_gateway", False):
            return "medium"
        else:
            return "low"

    def _assess_security_group_threat_level(self, sg: Dict[str, Any]) -> str:
        """Assess threat level for a security group."""
        ingress_rules = sg.get("ingress_rules", [])

        # Check for overly permissive rules
        for rule in ingress_rules:
            if isinstance(rule, dict):
                if rule.get("source") == "0.0.0.0/0" and rule.get("port") not in [80, 443]:
                    return "high"

        return "medium"

    def _assess_external_api_threat_level(self, dep: Dict[str, Any]) -> str:
        """Assess threat level for external API dependency."""
        data_class = dep.get("data_classification", "unknown")
        auth = dep.get("authentication", "unknown")

        if data_class in ["sensitive", "confidential"] and auth in ["none", "basic"]:
            return "high"
        elif data_class in ["sensitive", "confidential"]:
            return "medium"
        else:
            return "low"
