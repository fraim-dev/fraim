# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Data Flow Analysis Configuration

Provides configurable defaults and policies for data flow analysis,
allowing users to customize assumptions and behaviors based on their environment.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class DefaultSecurityPosture(Enum):
    """Default security posture for unknown configurations."""
    PERMISSIVE = "permissive"     # Assume least restrictive
    SECURE = "secure"             # Assume most secure
    ENVIRONMENT_BASED = "environment_based"  # Based on environment context


class DefaultEncryptionPolicy(Enum):
    """Default encryption policy for data flows."""
    ASSUME_ENCRYPTED = "assume_encrypted"     # Default to encrypted
    ASSUME_UNENCRYPTED = "assume_unencrypted"  # Default to unencrypted
    PORT_BASED = "port_based"                 # Based on port characteristics
    SERVICE_BASED = "service_based"           # Based on service type


@dataclass
class PortMappingOverrides:
    """Custom port mappings that override defaults."""
    custom_ports: Dict[int, Dict[str, str]] = field(default_factory=dict)

    # Format: {port: {"protocol": "HTTP", "service_name": "custom", "encryption": "true"}}


@dataclass
class ServicePatternOverrides:
    """Custom service patterns that override defaults."""
    custom_patterns: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Format: {"pattern_regex": {"service_type": "custom", "default_ports": "8080,8443"}}


@dataclass
class SecurityPolicyOverrides:
    """Security policy overrides for specific environments."""

    # Environment-specific encryption requirements
    require_encryption_for_environments: List[str] = field(
        default_factory=lambda: ["production", "prod"])

    # Service types that should always be encrypted
    always_encrypted_services: List[str] = field(
        default_factory=lambda: ["database", "auth", "payment"])

    # Default authentication assumptions by service type
    service_auth_defaults: Dict[str, str] = field(default_factory=lambda: {
        "database": "database_auth",
        "web": "session_based",
        "api": "token_based",
        "internal": "service_level"
    })

    # Default data classifications by service type
    service_data_classifications: Dict[str, str] = field(default_factory=lambda: {
        "database": "confidential",
        "auth": "restricted",
        "payment": "restricted",
        "logging": "internal",
        "monitoring": "internal"
    })


@dataclass
class AnalysisConfiguration:
    """Main configuration for data flow analysis."""

    # Default security posture
    default_security_posture: DefaultSecurityPosture = DefaultSecurityPosture.SECURE

    # Default encryption policy
    default_encryption_policy: DefaultEncryptionPolicy = DefaultEncryptionPolicy.PORT_BASED

    # Whether to enable intelligent service detection
    enable_service_detection: bool = True

    # Whether to analyze container configurations for security hints
    analyze_container_configs: bool = True

    # Whether to infer protocols from service names and ports
    enable_protocol_inference: bool = True

    # Custom overrides
    port_overrides: Optional[PortMappingOverrides] = None
    service_overrides: Optional[ServicePatternOverrides] = None
    security_overrides: Optional[SecurityPolicyOverrides] = None

    # Environment context for decision making
    target_environment: str = "production"  # production, staging, development

    # Risk tolerance settings
    assume_secure_by_default: bool = True
    classify_unknown_as_confidential: bool = False
    require_explicit_public_classification: bool = True

    def __post_init__(self) -> None:
        """Initialize default overrides if not provided."""
        if self.port_overrides is None:
            self.port_overrides = PortMappingOverrides()
        if self.service_overrides is None:
            self.service_overrides = ServicePatternOverrides()
        if self.security_overrides is None:
            self.security_overrides = SecurityPolicyOverrides()


@dataclass
class EnvironmentProfile:
    """Predefined configuration profiles for different environments."""
    name: str
    config: AnalysisConfiguration
    description: str


# Predefined environment profiles
ENVIRONMENT_PROFILES = {
    "production": EnvironmentProfile(
        name="production",
        description="Production environment with security-first assumptions",
        config=AnalysisConfiguration(
            default_security_posture=DefaultSecurityPosture.SECURE,
            default_encryption_policy=DefaultEncryptionPolicy.SERVICE_BASED,
            target_environment="production",
            assume_secure_by_default=True,
            classify_unknown_as_confidential=True,
            require_explicit_public_classification=True,
        )
    ),

    "development": EnvironmentProfile(
        name="development",
        description="Development environment with permissive assumptions",
        config=AnalysisConfiguration(
            default_security_posture=DefaultSecurityPosture.PERMISSIVE,
            default_encryption_policy=DefaultEncryptionPolicy.PORT_BASED,
            target_environment="development",
            assume_secure_by_default=False,
            classify_unknown_as_confidential=False,
            require_explicit_public_classification=False,
        )
    ),

    "staging": EnvironmentProfile(
        name="staging",
        description="Staging environment with balanced assumptions",
        config=AnalysisConfiguration(
            default_security_posture=DefaultSecurityPosture.ENVIRONMENT_BASED,
            default_encryption_policy=DefaultEncryptionPolicy.SERVICE_BASED,
            target_environment="staging",
            assume_secure_by_default=True,
            classify_unknown_as_confidential=False,
            require_explicit_public_classification=True,
        )
    ),

    "enterprise": EnvironmentProfile(
        name="enterprise",
        description="Enterprise environment with strict security requirements",
        config=AnalysisConfiguration(
            default_security_posture=DefaultSecurityPosture.SECURE,
            default_encryption_policy=DefaultEncryptionPolicy.ASSUME_ENCRYPTED,
            target_environment="production",
            assume_secure_by_default=True,
            classify_unknown_as_confidential=True,
            require_explicit_public_classification=True,
            security_overrides=SecurityPolicyOverrides(
                require_encryption_for_environments=[
                    "production", "staging", "pre-prod"],
                always_encrypted_services=[
                    "database", "auth", "payment", "api", "internal"],
                service_auth_defaults={
                    "database": "strong_auth",
                    "web": "multi_factor",
                    "api": "oauth2",
                    "internal": "mutual_tls"
                }
            )
        )
    )
}


def get_environment_config(environment: str) -> AnalysisConfiguration:
    """Get configuration for a specific environment."""
    profile = ENVIRONMENT_PROFILES.get(environment.lower())
    if profile:
        return profile.config

    # Default to production-like settings for unknown environments
    return ENVIRONMENT_PROFILES["production"].config


def load_custom_config(config_dict: Dict) -> AnalysisConfiguration:
    """Load configuration from a dictionary (e.g., from YAML/JSON file)."""
    # This would be implemented to load from external configuration files
    # For now, return default production config
    return get_environment_config("production")
