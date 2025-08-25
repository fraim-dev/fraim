# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Port and Protocol Mapping System

Provides intelligent mapping of ports to protocols, services, and security characteristics
based on well-known port assignments, service detection, and configuration analysis.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .flow_analysis_config import AnalysisConfiguration, get_environment_config
from .port_standards import PortStandardsRegistry, PortStandardLevel, PortStandard
from .iac_port_extractor import IaCPortExtractor, ExtractedPortMapping, PortMappingSource


class SecurityLevel(Enum):
    """Security level classifications."""
    UNKNOWN = "unknown"
    INSECURE = "insecure"
    BASIC = "basic"
    SECURE = "secure"
    HIGH_SECURITY = "high_security"


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


@dataclass
class PortProtocolInfo:
    """Information about a specific port/protocol combination."""
    protocol: str
    service_name: str
    description: str
    default_encryption: bool = False
    typical_auth: str = "unknown"
    data_classification: DataClassification = DataClassification.INTERNAL
    security_level: SecurityLevel = SecurityLevel.UNKNOWN
    direction: str = "bidirectional"


@dataclass
class ServiceTypeInfo:
    """Information about service types and their characteristics."""
    service_type: str
    typical_ports: List[int]
    protocols: List[str]
    requires_encryption: bool = False
    typical_auth: str = "unknown"
    data_classification: DataClassification = DataClassification.INTERNAL
    security_considerations: Optional[List[str]] = None


class PortProtocolMapper:
    """Maps ports and services to their expected protocols and security characteristics."""

    def __init__(self, config: Optional[AnalysisConfiguration] = None,
                 project_root: Optional[str] = None) -> None:
        """Initialize the port protocol mapper with optional configuration."""
        self.config = config or get_environment_config("production")
        self.port_registry = PortStandardsRegistry()

        # Confidence threshold for trusting port mappings based on environment
        confidence_map = {
            "production": "high",    # Only trust official IANA assignments
            "staging": "medium",     # Include widely adopted conventions
            "development": "low"     # Accept common conventions
        }
        self.confidence_threshold = confidence_map.get(
            self.config.target_environment, "medium")

        # IaC port extractor - extract actual port mappings from infrastructure files
        self.iac_extractor = IaCPortExtractor()
        self.iac_mappings: Dict[str, List[ExtractedPortMapping]] = {}

        # Extract IaC mappings if project root is provided
        if project_root:
            self.extract_iac_mappings(project_root)

        # Service type patterns and their characteristics
        self.service_patterns = {
            # Database patterns
            r"(mysql|mariadb)": ServiceTypeInfo("database", [3306], ["MySQL"], False, "database_auth", DataClassification.CONFIDENTIAL, ["sql_injection", "data_exposure"]),
            r"(postgres|postgresql)": ServiceTypeInfo("database", [5432], ["PostgreSQL"], False, "database_auth", DataClassification.CONFIDENTIAL, ["sql_injection", "data_exposure"]),
            r"(redis|valkey)": ServiceTypeInfo("cache", [6379], ["Redis"], False, "optional", DataClassification.INTERNAL, ["data_exposure", "cache_poisoning"]),
            r"mongodb": ServiceTypeInfo("database", [27017], ["MongoDB"], False, "database_auth", DataClassification.CONFIDENTIAL, ["nosql_injection", "data_exposure"]),

            # Web service patterns
            r"(nginx|httpd|apache)": ServiceTypeInfo("web_server", [80, 443], ["HTTP", "HTTPS"], True, "various", DataClassification.INTERNAL, ["web_vulnerabilities", "ddos"]),
            r"(node|express)": ServiceTypeInfo("web_app", [3000, 8080], ["HTTP"], False, "application", DataClassification.INTERNAL, ["code_injection", "xss"]),
            r"(django|flask|fastapi)": ServiceTypeInfo("web_app", [8000, 8080], ["HTTP"], False, "application", DataClassification.INTERNAL, ["code_injection", "xss"]),
            r"(spring|tomcat)": ServiceTypeInfo("web_app", [8080, 8443], ["HTTP", "HTTPS"], True, "application", DataClassification.INTERNAL, ["code_injection", "deserialization"]),

            # Message queue patterns
            r"(rabbitmq|amqp)": ServiceTypeInfo("message_queue", [5672], ["AMQP"], False, "basic", DataClassification.INTERNAL, ["message_tampering", "unauthorized_access"]),
            r"kafka": ServiceTypeInfo("message_queue", [9092], ["Kafka"], False, "optional", DataClassification.INTERNAL, ["message_tampering", "unauthorized_access"]),
            r"(activemq|artemis)": ServiceTypeInfo("message_queue", [61616], ["JMS"], False, "basic", DataClassification.INTERNAL, ["message_tampering", "unauthorized_access"]),

            # Search/Analytics patterns
            r"elasticsearch": ServiceTypeInfo("search", [9200], ["HTTP"], False, "basic", DataClassification.INTERNAL, ["data_exposure", "unauthorized_access"]),
            r"kibana": ServiceTypeInfo("visualization", [5601], ["HTTP"], False, "basic", DataClassification.INTERNAL, ["data_exposure", "unauthorized_access"]),

            # Monitoring patterns
            r"prometheus": ServiceTypeInfo("monitoring", [9090], ["HTTP"], False, "basic", DataClassification.INTERNAL, ["metrics_exposure", "unauthorized_access"]),
            r"grafana": ServiceTypeInfo("visualization", [3000], ["HTTP"], False, "basic", DataClassification.INTERNAL, ["data_exposure", "unauthorized_access"]),

            # Proxy/Load balancer patterns
            r"(haproxy|envoy|traefik)": ServiceTypeInfo("load_balancer", [80, 443, 8080], ["HTTP", "HTTPS"], True, "various", DataClassification.INTERNAL, ["ddos", "routing_bypass"]),
        }

    def analyze_port(self, port: int, service_name: Optional[str] = None,
                     container_config: Optional[Dict[str, Any]] = None) -> PortProtocolInfo:
        """
        Analyze a port to determine its protocol and characteristics.

        Args:
            port: The port number to analyze
            service_name: Optional service name for additional context
            container_config: Optional container configuration for more context

        Returns:
            PortProtocolInfo with inferred characteristics
        """
        # Check if we should trust the port mapping based on standardization level
        port_standard = self.port_registry.get_port_standard(port)

        if port_standard and self.port_registry.should_trust_mapping(port, self.confidence_threshold):
            # Use trusted port mapping
            base_info = self._create_port_info_from_standard(port_standard)
        else:
            # Fallback to inference for unknown or untrusted ports
            base_info = self._infer_port_info(port)

            # Add metadata about reliability
            if port_standard:
                reliability = self.port_registry.get_reliability_level(port)
                base_info.description += f" (Reliability: {reliability})"

        # Enhance with service-specific information
        if service_name or container_config:
            enhanced_info = self._enhance_with_service_info(
                base_info, service_name, container_config)
            return enhanced_info

        return base_info

    def _create_port_info_from_standard(self, port_standard: PortStandard) -> PortProtocolInfo:
        """Create PortProtocolInfo from a PortStandard."""
        # Map service names to appropriate security characteristics
        service_security_map = {
            "http": (False, "none", DataClassification.PUBLIC, SecurityLevel.INSECURE),
            "https": (True, "certificates", DataClassification.INTERNAL, SecurityLevel.SECURE),
            "ssh": (True, "key_based", DataClassification.RESTRICTED, SecurityLevel.SECURE),
            "mysql": (False, "database_auth", DataClassification.CONFIDENTIAL, SecurityLevel.BASIC),
            "postgresql": (False, "database_auth", DataClassification.CONFIDENTIAL, SecurityLevel.BASIC),
            "redis": (False, "optional", DataClassification.INTERNAL, SecurityLevel.BASIC),
            "mongodb": (False, "database_auth", DataClassification.CONFIDENTIAL, SecurityLevel.BASIC),
        }

        # Get security characteristics or use defaults
        service_name = port_standard.service_name.lower()
        encryption, auth, data_class, sec_level = service_security_map.get(
            service_name,
            (False, "unknown", DataClassification.INTERNAL, SecurityLevel.UNKNOWN)
        )

        # Enhance description with source information
        description = f"{port_standard.notes or port_standard.service_name} (Source: {port_standard.source})"

        return PortProtocolInfo(
            protocol=port_standard.protocol,
            service_name=service_name,
            description=description,
            default_encryption=encryption,
            typical_auth=auth,
            data_classification=data_class,
            security_level=sec_level,
            direction="bidirectional"
        )

    def _infer_port_info(self, port: int) -> PortProtocolInfo:
        """Infer port information based on common port ranges and patterns."""
        # Common port range patterns
        if port == 80:
            return PortProtocolInfo("HTTP", "web", "HTTP service", False, "none", DataClassification.PUBLIC, SecurityLevel.INSECURE)
        elif port == 443:
            return PortProtocolInfo("HTTPS", "web", "HTTPS service", True, "certificates", DataClassification.INTERNAL, SecurityLevel.SECURE)
        elif 8000 <= port <= 8999:
            # Common web application range
            encryption = port % 1000 >= 443  # 8443, 8843, etc.
            protocol = "HTTPS" if encryption else "HTTP"
            security = SecurityLevel.SECURE if encryption else SecurityLevel.BASIC
            return PortProtocolInfo(protocol, "web_app", "Web application", encryption, "application", DataClassification.INTERNAL, security)
        elif 9000 <= port <= 9999:
            # Common monitoring/admin range
            return PortProtocolInfo("HTTP", "admin", "Administrative service", False, "basic", DataClassification.CONFIDENTIAL, SecurityLevel.BASIC)
        elif 3000 <= port <= 3999:
            # Common development/database range
            return PortProtocolInfo("HTTP", "development", "Development service", False, "basic", DataClassification.INTERNAL, SecurityLevel.BASIC)
        elif 5000 <= port <= 5999:
            # Common database/service range
            return PortProtocolInfo("TCP", "database", "Database service", False, "database_auth", DataClassification.CONFIDENTIAL, SecurityLevel.BASIC)
        elif port >= 10000:
            # High ports - typically custom services
            return PortProtocolInfo("TCP", "custom", "Custom service", False, "unknown", DataClassification.INTERNAL, SecurityLevel.UNKNOWN)
        else:
            # Default for unknown ports
            return PortProtocolInfo("TCP", "unknown", "Unknown service", False, "unknown", DataClassification.INTERNAL, SecurityLevel.UNKNOWN)

    def _enhance_with_service_info(self, base_info: PortProtocolInfo, service_name: Optional[str],
                                   container_config: Optional[Dict[str, Any]]) -> PortProtocolInfo:
        """Enhance port info with service-specific details."""
        enhanced_info = base_info

        # Check service name patterns
        if service_name:
            service_info = self._match_service_pattern(service_name)
            if service_info:
                enhanced_info = self._merge_service_info(
                    base_info, service_info)

        # Check container configuration
        if container_config:
            config_info = self._analyze_container_config(container_config)
            enhanced_info = self._merge_config_info(enhanced_info, config_info)

        return enhanced_info

    def _match_service_pattern(self, service_name: str) -> Optional[ServiceTypeInfo]:
        """Match service name against known patterns."""
        service_lower = service_name.lower()

        for pattern, service_info in self.service_patterns.items():
            if re.search(pattern, service_lower):
                return service_info

        return None

    def _analyze_container_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze container configuration for security and protocol hints."""
        analysis: Dict[str, Any] = {
            "encryption_hints": [],
            "auth_hints": [],
            "protocol_hints": [],
            "security_level": SecurityLevel.UNKNOWN
        }

        # Check base image for service type hints
        base_image = config.get("base_image", "").lower()
        if base_image:
            if any(db in base_image for db in ["mysql", "postgres", "mongo", "redis"]):
                analysis["protocol_hints"].append("database")
                analysis["security_level"] = SecurityLevel.BASIC
            elif any(web in base_image for web in ["nginx", "apache", "httpd"]):
                analysis["protocol_hints"].append("web")
            elif "alpine" in base_image or "ubuntu" in base_image:
                # Base OS images - look for other hints
                pass

        # Check environment variables for security hints
        env_vars = config.get("environment_variables", [])
        for var in env_vars:
            var_lower = str(var).lower()
            if any(term in var_lower for term in ["ssl", "tls", "cert", "key"]):
                analysis["encryption_hints"].append("ssl_configured")
                analysis["security_level"] = SecurityLevel.SECURE
            elif any(term in var_lower for term in ["auth", "token", "password"]):
                analysis["auth_hints"].append("auth_configured")

        # Check volume mounts for security-related paths
        volumes = config.get("volume_mounts", [])
        for volume in volumes:
            volume_lower = str(volume).lower()
            if any(path in volume_lower for path in ["/etc/ssl", "/etc/tls", "/certs"]):
                analysis["encryption_hints"].append("cert_volume")
                analysis["security_level"] = SecurityLevel.SECURE

        return analysis

    def _merge_service_info(self, port_info: PortProtocolInfo, service_info: ServiceTypeInfo) -> PortProtocolInfo:
        """Merge service type information with port information."""
        # Use service info to override defaults where appropriate
        protocol = service_info.protocols[0] if service_info.protocols else port_info.protocol
        encryption = service_info.requires_encryption or port_info.default_encryption
        auth = service_info.typical_auth if service_info.typical_auth != "unknown" else port_info.typical_auth
        data_class = service_info.data_classification

        # Determine security level based on encryption and auth
        if encryption and auth not in ["none", "unknown"]:
            security_level = SecurityLevel.SECURE
        elif encryption or auth not in ["none", "unknown"]:
            security_level = SecurityLevel.BASIC
        else:
            security_level = SecurityLevel.INSECURE

        return PortProtocolInfo(
            protocol=protocol,
            service_name=service_info.service_type,
            description=f"{service_info.service_type} service",
            default_encryption=encryption,
            typical_auth=auth,
            data_classification=data_class,
            security_level=security_level,
            direction=port_info.direction
        )

    def _merge_config_info(self, port_info: PortProtocolInfo, config_info: Dict[str, Any]) -> PortProtocolInfo:
        """Merge container configuration analysis with port information."""
        # Update encryption based on config hints
        encryption = port_info.default_encryption
        if config_info["encryption_hints"]:
            encryption = True

        # Update auth based on config hints
        auth = port_info.typical_auth
        if config_info["auth_hints"] and auth in ["none", "unknown"]:
            auth = "configured"

        # Update security level based on analysis
        security_level = port_info.security_level
        if config_info["security_level"] != SecurityLevel.UNKNOWN:
            security_level = config_info["security_level"]

        return PortProtocolInfo(
            protocol=port_info.protocol,
            service_name=port_info.service_name,
            description=port_info.description,
            default_encryption=encryption,
            typical_auth=auth,
            data_classification=port_info.data_classification,
            security_level=security_level,
            direction=port_info.direction
        )

    def analyze_service_communication(self, source_service: str, target_service: str,
                                      port: Optional[int] = None) -> Dict[str, Any]:
        """Analyze communication between two services."""
        # Determine likely protocol and security based on service types
        source_info = self._match_service_pattern(source_service)
        target_info = self._match_service_pattern(target_service)

        # Default communication characteristics
        protocol = "HTTP"
        encryption = False
        auth = "service_level"
        data_class = DataClassification.INTERNAL

        # If we have port information, use it
        if port:
            port_info = self.analyze_port(port, target_service)
            protocol = port_info.protocol
            encryption = port_info.default_encryption
            if port_info.typical_auth != "unknown":
                auth = port_info.typical_auth

        # Enhance based on service types
        if target_info:
            if target_info.requires_encryption:
                encryption = True
                protocol = "HTTPS" if protocol == "HTTP" else protocol
            if target_info.typical_auth != "unknown":
                auth = target_info.typical_auth
            data_class = target_info.data_classification

        # Determine security level
        if encryption and auth not in ["none", "unknown"]:
            security_level = SecurityLevel.SECURE
        elif encryption or auth not in ["none", "unknown"]:
            security_level = SecurityLevel.BASIC
        else:
            security_level = SecurityLevel.INSECURE

        return {
            "protocol": protocol,
            "encryption": encryption,
            "authentication": auth,
            "data_classification": data_class.value,
            "security_level": security_level.value,
            "inferred_port": port or (443 if encryption else 80)
        }

    def get_port_mapping_report(self) -> Dict[str, Any]:
        """
        Generate a report on the reliability and sources of port mappings used.

        This helps users understand what assumptions are being made and how reliable they are.
        """
        return self.port_registry.validate_assumptions()

    def log_port_assumptions(self, logger: Any) -> None:
        """Log information about port mapping assumptions for transparency."""
        report = self.get_port_mapping_report()

        logger.info(f"Port Mapping Configuration:")
        logger.info(f"  Environment: {self.config.target_environment}")
        logger.info(f"  Confidence Threshold: {self.confidence_threshold}")
        logger.info(f"  Total known ports: {report['total_ports']}")
        logger.info(f"  Official IANA ports: {report['official_iana']}")
        logger.info(f"  Uncertain mappings: {report['uncertain_mappings']}")

        for recommendation in report["recommendations"]:
            logger.warning(f"  Recommendation: {recommendation}")

        # Log reliability breakdown
        logger.info("Port reliability breakdown:")
        for level, count in report["by_reliability"].items():
            if count > 0:
                logger.info(f"  {level}: {count} ports")

    def is_port_mapping_reliable(self, port: int) -> Tuple[bool, str]:
        """
        Check if a port mapping is reliable and return explanation.

        Returns:
            (is_reliable, explanation)
        """
        port_standard = self.port_registry.get_port_standard(port)

        if not port_standard:
            return False, f"Port {port} has no known standard mapping"

        reliability = self.port_registry.get_reliability_level(port)
        is_trusted = self.port_registry.should_trust_mapping(
            port, self.confidence_threshold)
        source = port_standard.source

        explanation = f"Port {port}: {reliability} (Source: {source})"

        return is_trusted, explanation

    def extract_iac_mappings(self, project_root: str) -> None:
        """Extract port mappings from Infrastructure as Code files."""
        from pathlib import Path

        try:
            extracted_mappings = self.iac_extractor.extract_from_directory(
                Path(project_root))
            self.iac_mappings = self.iac_extractor.get_port_mappings_by_service()

            # Log what we found
            report = self.iac_extractor.get_mapping_report()
            print(f"IaC Port Extraction Results:")
            print(f"  Total mappings found: {report['total_mappings']}")
            print(f"  Services discovered: {report['unique_services']}")
            print(f"  Files processed: {report['files_processed']}")

            for source, count in report['sources'].items():
                print(f"  From {source}: {count} mappings")

        except Exception as e:
            print(f"Warning: Could not extract IaC port mappings: {e}")

    def get_iac_port_for_service(self, service_name: str) -> Optional[ExtractedPortMapping]:
        """Get the primary port mapping for a service from IaC files."""
        mappings = self.iac_mappings.get(service_name, [])

        if not mappings:
            # Try fuzzy matching
            for iac_service_name, iac_mappings in self.iac_mappings.items():
                if (service_name.lower() in iac_service_name.lower() or
                        iac_service_name.lower() in service_name.lower()):
                    mappings = iac_mappings
                    break

        if mappings:
            # Return the mapping with highest confidence
            return max(mappings, key=lambda m: m.confidence)

        return None

    def analyze_port_with_iac_priority(self, port: int, service_name: Optional[str] = None,
                                       container_config: Optional[Dict[str, Any]] = None) -> PortProtocolInfo:
        """
        Analyze a port with IaC mappings taking priority over standards-based assumptions.

        Priority order:
        1. Exact IaC mapping for this service/port combination
        2. IaC mapping for this service (different port)  
        3. Standards-based port mapping
        4. Inference from service name/container config
        """

        # Priority 1: Check for exact IaC mapping
        if service_name:
            iac_mapping = self.get_iac_port_for_service(service_name)
            if iac_mapping and iac_mapping.container_port == port:
                return self._create_port_info_from_iac(iac_mapping)

        # Priority 2: Check for IaC mapping with different port (service name match)
        if service_name:
            iac_mapping = self.get_iac_port_for_service(service_name)
            if iac_mapping:
                # Use IaC info but with the provided port
                port_info = self._create_port_info_from_iac(iac_mapping)
                port_info.description += f" (Port {port} differs from IaC port {iac_mapping.container_port})"
                return port_info

        # Priority 3 & 4: Fall back to original standards-based analysis
        return self.analyze_port(port, service_name, container_config)

    def _create_port_info_from_iac(self, iac_mapping: ExtractedPortMapping) -> PortProtocolInfo:
        """Create PortProtocolInfo from an IaC-extracted mapping."""

        # Determine security characteristics based on source and protocol
        if iac_mapping.source in [PortMappingSource.DOCKER_COMPOSE, PortMappingSource.KUBERNETES_MANIFEST]:
            # High confidence in IaC sources
            encryption = self._infer_encryption_from_iac(iac_mapping)
            auth = self._infer_auth_from_iac(iac_mapping)
            data_class = self._infer_data_class_from_iac(iac_mapping)
            security_level = self._infer_security_level_from_iac(iac_mapping)
        else:
            # Lower confidence sources, use defaults
            encryption = False
            auth = "unknown"
            data_class = DataClassification.INTERNAL
            security_level = SecurityLevel.UNKNOWN

        # Enhance description with IaC source info
        source_info = f"from {iac_mapping.source.value}"
        if iac_mapping.source_file:
            source_info += f" ({iac_mapping.source_file})"

        description = f"{iac_mapping.service_name} port {iac_mapping.container_port} ({source_info})"

        return PortProtocolInfo(
            protocol=iac_mapping.protocol,
            service_name=iac_mapping.service_name,
            description=description,
            default_encryption=encryption,
            typical_auth=auth,
            data_classification=data_class,
            security_level=security_level,
            direction="bidirectional"
        )

    def _infer_encryption_from_iac(self, mapping: ExtractedPortMapping) -> bool:
        """Infer encryption based on IaC mapping characteristics."""
        # Check port number
        if mapping.container_port in [443, 8443, 9443]:
            return True

        # Check context
        context = mapping.context or {}
        if any(term in str(context).lower() for term in ['tls', 'ssl', 'https', 'secure']):
            return True

        return False

    def _infer_auth_from_iac(self, mapping: ExtractedPortMapping) -> str:
        """Infer authentication based on IaC mapping characteristics."""
        service_name = mapping.service_name.lower()

        if any(db in service_name for db in ['mysql', 'postgres', 'mongo', 'redis']):
            return "database_auth"
        elif 'auth' in service_name or 'login' in service_name:
            return "token_based"
        elif mapping.container_port == 22:
            return "key_based"
        else:
            return "unknown"

    def _infer_data_class_from_iac(self, mapping: ExtractedPortMapping) -> DataClassification:
        """Infer data classification based on IaC mapping characteristics."""
        service_name = mapping.service_name.lower()

        if any(db in service_name for db in ['mysql', 'postgres', 'mongo']):
            return DataClassification.CONFIDENTIAL
        elif any(term in service_name for term in ['auth', 'secret', 'key']):
            return DataClassification.RESTRICTED
        elif any(term in service_name for term in ['public', 'web', 'frontend']):
            return DataClassification.PUBLIC
        else:
            return DataClassification.INTERNAL

    def _infer_security_level_from_iac(self, mapping: ExtractedPortMapping) -> SecurityLevel:
        """Infer security level based on IaC mapping characteristics."""
        if mapping.confidence >= 0.9:
            if self._infer_encryption_from_iac(mapping):
                return SecurityLevel.SECURE
            else:
                return SecurityLevel.BASIC
        else:
            return SecurityLevel.UNKNOWN
