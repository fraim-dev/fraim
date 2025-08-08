# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Trust Boundary Analyzer

Handles identification, analysis, and prioritization of trust boundaries
from infrastructure and API discovery results.
"""

from typing import Any, Dict, List

from fraim.config import Config

from .types import ComponentDiscoveryResults, TrustBoundary


class TrustBoundaryAnalyzer:
    """Analyzes trust boundaries from component discovery results."""

    def __init__(self, config: Config):
        self.config = config

    async def analyze_trust_boundaries(self, results: ComponentDiscoveryResults) -> List[Dict[str, Any]]:
        """Main entry point for trust boundary analysis."""
        try:
            self.config.logger.info("Starting trust boundary analysis")
            trust_boundaries = []

            # Debug: Log what data we have
            self.config.logger.info(f"Infrastructure data available: {results.infrastructure is not None}")
            self.config.logger.info(f"API interfaces data available: {results.api_interfaces is not None}")

            # Identify network-level trust boundaries from infrastructure
            if results.infrastructure:
                self.config.logger.info("Processing infrastructure trust boundaries")
                network_boundaries = self._identify_network_trust_boundaries(results.infrastructure)
                trust_boundaries.extend(network_boundaries)
                self.config.logger.info(f"Found {len(network_boundaries)} infrastructure trust boundaries")

            # Identify application-level trust boundaries from APIs
            if results.api_interfaces:
                self.config.logger.info("Processing API trust boundaries")
                api_boundaries = self._identify_api_trust_boundaries(results.api_interfaces)
                trust_boundaries.extend(api_boundaries)
                self.config.logger.info(f"Found {len(api_boundaries)} API trust boundaries")

            # Analyze and prioritize boundaries
            analyzed_boundaries = self._analyze_trust_boundaries(trust_boundaries)

            self.config.logger.info(f"Analyzed {len(analyzed_boundaries)} trust boundaries")
            return analyzed_boundaries

        except Exception as e:
            self.config.logger.error(f"Trust boundary analysis failed: {str(e)}")
            import traceback

            self.config.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

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
