# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Port Standards and Registry

Provides port mappings based on official IANA assignments and well-documented industry standards.
Clearly distinguishes between officially registered ports and commonly-used conventions.
"""

from typing import Any, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class PortStandardLevel(Enum):
    """Level of standardization for port assignments."""
    IANA_WELL_KNOWN = "iana_well_known"           # Official IANA Well-Known Ports (0-1023)
    # Official IANA Registered Ports (1024-49151)
    IANA_REGISTERED = "iana_registered"
    # Not IANA but widely used by convention
    WIDELY_ADOPTED = "widely_adopted"
    # Vendor-specific default but configurable
    VENDOR_DEFAULT = "vendor_default"
    COMMON_CONVENTION = "common_convention"       # Common usage but not universal
    UNCERTAIN = "uncertain"                       # Uncertain or varies by deployment


@dataclass
class PortStandard:
    """Information about a port's standardization level and source."""
    port: int
    service_name: str
    protocol: str
    standard_level: PortStandardLevel
    source: str  # Reference to documentation/standard
    notes: Optional[str] = None


# Official IANA Well-Known Ports (0-1023)
# Source: https://www.iana.org/assignments/service-names-port-numbers/
IANA_WELL_KNOWN_PORTS = {
    20: PortStandard(20, "ftp-data", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 959", "File Transfer Protocol Data"),
    21: PortStandard(21, "ftp", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 959", "File Transfer Protocol Control"),
    22: PortStandard(22, "ssh", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 4251", "Secure Shell"),
    23: PortStandard(23, "telnet", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 854", "Telnet Protocol"),
    25: PortStandard(25, "smtp", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 5321", "Simple Mail Transfer Protocol"),
    53: PortStandard(53, "domain", "TCP/UDP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 1035", "Domain Name System"),
    67: PortStandard(67, "bootps", "UDP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 2131", "Bootstrap Protocol Server"),
    68: PortStandard(68, "bootpc", "UDP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 2131", "Bootstrap Protocol Client"),
    69: PortStandard(69, "tftp", "UDP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 1350", "Trivial File Transfer Protocol"),
    80: PortStandard(80, "http", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                     "RFC 7230", "Hypertext Transfer Protocol"),
    110: PortStandard(110, "pop3", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 1939", "Post Office Protocol v3"),
    123: PortStandard(123, "ntp", "UDP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 5905", "Network Time Protocol"),
    143: PortStandard(143, "imap", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 3501", "Internet Message Access Protocol"),
    443: PortStandard(443, "https", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 2818", "HTTP over TLS/SSL"),
    993: PortStandard(993, "imaps", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 8314", "IMAP over TLS/SSL"),
    995: PortStandard(995, "pop3s", "TCP", PortStandardLevel.IANA_WELL_KNOWN,
                      "RFC 8314", "POP3 over TLS/SSL"),
}

# Official IANA Registered Ports (1024-49151) - Selected commonly used ones
# Source: https://www.iana.org/assignments/service-names-port-numbers/
IANA_REGISTERED_PORTS = {
    1433: PortStandard(1433, "ms-sql-s", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "IANA Registry", "Microsoft SQL Server"),
    1521: PortStandard(1521, "oracle", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "IANA Registry", "Oracle database"),
    3306: PortStandard(3306, "mysql", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "IANA Registry", "MySQL Database System"),
    3389: PortStandard(3389, "ms-wbt-server", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "IANA Registry", "Microsoft Terminal Server (RDP)"),
    5060: PortStandard(5060, "sip", "TCP/UDP", PortStandardLevel.IANA_REGISTERED,
                       "RFC 3261", "Session Initiation Protocol"),
    5432: PortStandard(5432, "postgresql", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "IANA Registry", "PostgreSQL Database"),
    5672: PortStandard(5672, "amqp", "TCP", PortStandardLevel.IANA_REGISTERED,
                       "RFC 2960", "Advanced Message Queuing Protocol"),
}

# Widely adopted conventions (not IANA registered but commonly used)
WIDELY_ADOPTED_PORTS = {
    6379: PortStandard(6379, "redis", "TCP", PortStandardLevel.WIDELY_ADOPTED,
                       "Redis Documentation", "Redis default port"),
    8080: PortStandard(8080, "http-alt", "TCP", PortStandardLevel.WIDELY_ADOPTED,
                       "Common Convention", "Alternative HTTP port"),
    8443: PortStandard(8443, "https-alt", "TCP", PortStandardLevel.WIDELY_ADOPTED,
                       "Common Convention", "Alternative HTTPS port"),
    9200: PortStandard(9200, "elasticsearch", "TCP", PortStandardLevel.WIDELY_ADOPTED,
                       "Elasticsearch Documentation", "Elasticsearch REST API"),
    11211: PortStandard(11211, "memcache", "TCP", PortStandardLevel.WIDELY_ADOPTED,
                        "Memcached Documentation", "Memcached default port"),
}

# Vendor-specific defaults (configurable but commonly used)
VENDOR_DEFAULT_PORTS = {
    27017: PortStandard(27017, "mongodb", "TCP", PortStandardLevel.VENDOR_DEFAULT,
                        "MongoDB Documentation", "MongoDB default port - configurable"),
    9092: PortStandard(9092, "kafka", "TCP", PortStandardLevel.VENDOR_DEFAULT,
                       "Apache Kafka Documentation", "Kafka broker default port - configurable"),
    6443: PortStandard(6443, "kubernetes-api", "TCP", PortStandardLevel.VENDOR_DEFAULT,
                       "Kubernetes Documentation", "Kubernetes API server default - configurable"),
    2376: PortStandard(2376, "docker-tls", "TCP", PortStandardLevel.VENDOR_DEFAULT,
                       "Docker Documentation", "Docker daemon with TLS - configurable"),
    2375: PortStandard(2375, "docker", "TCP", PortStandardLevel.VENDOR_DEFAULT,
                       "Docker Documentation", "Docker daemon insecure - configurable"),
}

# Common conventions (usage varies)
COMMON_CONVENTION_PORTS = {
    3000: PortStandard(3000, "dev-server", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Development Convention", "Common development server port"),
    5000: PortStandard(5000, "flask-dev", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Flask Documentation", "Flask development server default"),
    5601: PortStandard(5601, "kibana", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Kibana Documentation", "Kibana web interface"),
    8000: PortStandard(8000, "http-dev", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Development Convention", "Alternative HTTP development port"),
    9000: PortStandard(9000, "admin", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Common Convention", "Administrative interfaces"),
    9090: PortStandard(9090, "prometheus", "TCP", PortStandardLevel.COMMON_CONVENTION,
                       "Prometheus Documentation", "Prometheus metrics server"),
}


class PortStandardsRegistry:
    """Registry for looking up port standards and reliability levels."""

    def __init__(self) -> None:
        # Combine all port mappings
        self.standards: Dict[int, PortStandard] = {}
        self.standards.update(IANA_WELL_KNOWN_PORTS)
        self.standards.update(IANA_REGISTERED_PORTS)
        self.standards.update(WIDELY_ADOPTED_PORTS)
        self.standards.update(VENDOR_DEFAULT_PORTS)
        self.standards.update(COMMON_CONVENTION_PORTS)

        # Create reverse lookup by service name
        self.service_to_port: Dict[str, int] = {}
        for port, standard in self.standards.items():
            self.service_to_port[standard.service_name] = port

    def get_port_standard(self, port: int) -> Optional[PortStandard]:
        """Get standardization information for a port."""
        return self.standards.get(port)

    def get_service_port(self, service_name: str) -> Optional[int]:
        """Get default port for a service name."""
        return self.service_to_port.get(service_name.lower())

    def get_reliability_level(self, port: int) -> str:
        """Get a human-readable reliability level for port mapping."""
        standard = self.get_port_standard(port)
        if not standard:
            return "Unknown - no standard found"

        reliability_map = {
            PortStandardLevel.IANA_WELL_KNOWN: "Very High - Official IANA Well-Known Port",
            PortStandardLevel.IANA_REGISTERED: "High - Official IANA Registered Port",
            PortStandardLevel.WIDELY_ADOPTED: "Medium-High - Widely adopted industry convention",
            PortStandardLevel.VENDOR_DEFAULT: "Medium - Vendor default (configurable)",
            PortStandardLevel.COMMON_CONVENTION: "Medium-Low - Common convention (varies)",
            PortStandardLevel.UNCERTAIN: "Low - Uncertain or highly variable"
        }

        return reliability_map.get(standard.standard_level, "Unknown")

    def get_official_ports(self) -> Set[int]:
        """Get set of ports with official IANA assignments."""
        return {port for port, standard in self.standards.items()
                if standard.standard_level in [PortStandardLevel.IANA_WELL_KNOWN,
                                               PortStandardLevel.IANA_REGISTERED]}

    def get_uncertain_ports(self) -> Set[int]:
        """Get set of ports with uncertain or conventional mappings."""
        return {port for port, standard in self.standards.items()
                if standard.standard_level in [PortStandardLevel.COMMON_CONVENTION,
                                               PortStandardLevel.UNCERTAIN]}

    def should_trust_mapping(self, port: int, confidence_threshold: str = "medium") -> bool:
        """
        Determine if we should trust a port mapping based on confidence threshold.

        Args:
            port: The port number
            confidence_threshold: "high", "medium", or "low"
        """
        standard = self.get_port_standard(port)
        if not standard:
            return confidence_threshold == "low"

        confidence_levels = {
            "high": [PortStandardLevel.IANA_WELL_KNOWN, PortStandardLevel.IANA_REGISTERED],
            "medium": [PortStandardLevel.IANA_WELL_KNOWN, PortStandardLevel.IANA_REGISTERED,
                       PortStandardLevel.WIDELY_ADOPTED, PortStandardLevel.VENDOR_DEFAULT],
            "low": list(PortStandardLevel)  # All levels
        }

        return standard.standard_level in confidence_levels.get(confidence_threshold, [])

    def get_mapping_source(self, port: int) -> Optional[str]:
        """Get the source/documentation for a port mapping."""
        standard = self.get_port_standard(port)
        return standard.source if standard else None

    def validate_assumptions(self) -> Dict[str, Any]:
        """Validate and report on the assumptions made in port mappings."""
        total_ports = len(self.standards)
        official_iana = len(self.get_official_ports())
        uncertain_mappings = len(self.get_uncertain_ports())

        report: Dict[str, Any] = {
            "total_ports": total_ports,
            "official_iana": official_iana,
            "uncertain_mappings": uncertain_mappings,
            "by_reliability": {},
            "recommendations": []
        }

        # Count by reliability level
        reliability_dict: Dict[str, int] = {}
        for level in PortStandardLevel:
            count = len([s for s in self.standards.values()
                        if s.standard_level == level])
            reliability_dict[level.value] = count
        report["by_reliability"] = reliability_dict

        # Add recommendations
        recommendations = []
        if uncertain_mappings > 0:
            recommendations.append(
                f"Consider additional verification for {uncertain_mappings} "
                "ports with uncertain mappings"
            )

        if total_ports > 0 and official_iana / total_ports < 0.5:
            recommendations.append(
                "Consider prioritizing officially registered ports over conventions"
            )

        report["recommendations"] = recommendations
        return report
