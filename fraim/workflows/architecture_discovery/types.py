# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Discovery Types

Data classes and type definitions for the Architecture Discovery workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel

from fraim.core.workflows import ChunkWorkflowInput


@dataclass
class ArchitectureDiscoveryInput(ChunkWorkflowInput):
    """Input for the Architecture Discovery orchestrator workflow."""

    # Architecture-specific configuration options
    diagram_format: Annotated[
        str, {"help": "Output format for architecture diagrams (currently only mermaid supported)"}
    ] = "mermaid"

    # Rate limiting configuration
    api_delay_seconds: Annotated[float, {"help": "Delay between API calls to respect rate limits"}] = 0.5

    reduce_concurrency_on_rate_limit: Annotated[
        bool, {"help": "Automatically reduce concurrency when rate limits are hit"}
    ] = True

    # File override options for bypassing sub-workflow execution
    infrastructure_file: Annotated[
        Optional[str], {"help": "Path to JSON file containing infrastructure discovery results to use instead of running infrastructure discovery"}
    ] = None

    api_interfaces_file: Annotated[
        Optional[str], {"help": "Path to JSON file containing API interface discovery results to use instead of running API discovery"}
    ] = None


# Unified Component Model for Architecture Discovery

@dataclass
class UnifiedComponent:
    """Unified representation of a system component (infrastructure + API interfaces)."""

    # Core component identity
    component_id: str
    component_name: str
    # service, database, cache, load_balancer, queue, storage, cdn, proxy, gateway, other
    component_type: str
    description: Optional[str] = None

    # Infrastructure characteristics (from infrastructure discovery)
    # provider, service_name, configuration, etc.
    infrastructure_details: Optional[Dict[str, Any]] = None
    # container configs, resource limits, environments
    deployment_info: Optional[Dict[str, Any]] = None

    # API interface characteristics (from API discovery)
    # REST endpoints, GraphQL schema, WebSocket connections
    api_interfaces: Optional[List[Dict[str, Any]]] = None
    # data models used by this component
    data_models: Optional[List[Dict[str, Any]]] = None

    # Component relationships and connectivity
    # other components this depends on
    dependencies: List[str] = field(default_factory=list)
    # other components that depend on this
    dependents: List[str] = field(default_factory=list)

    # Network and communication details
    exposed_ports: List[int] = field(default_factory=list)
    # http, https, tcp, udp, grpc, etc.
    protocols: List[str] = field(default_factory=list)
    # public endpoints exposed by this component
    endpoints: List[str] = field(default_factory=list)

    # Security and trust information
    # will be populated by trust boundary analysis
    trust_zone: Optional[str] = None
    security_controls: List[str] = field(default_factory=list)
    authentication_methods: List[str] = field(default_factory=list)

    # Metadata
    confidence: float = 0.0
    # files where this component was discovered
    source_files: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UnifiedComponentDiscovery:
    """Results of unified component discovery phase."""

    components: List[UnifiedComponent] = field(default_factory=list)
    component_relationships: List[Dict[str, Any]] = field(
        default_factory=list)  # discovered relationships between components
    summary: Optional[Dict[str, Any]] = None
    confidence: float = 0.0


@dataclass
class ComponentDiscoveryResults:
    """Container for component discovery results."""

    # Unified Component Discovery Results
    unified_components: Optional[UnifiedComponentDiscovery] = None

    # Legacy Discovery Results (still needed for backward compatibility and synthesis)
    infrastructure: Optional[Dict[str, Any]] = None
    api_interfaces: Optional[Dict[str, Any]] = None

    # Synthesis results
    architecture_diagram: Optional[str] = None
    data_flows: Optional[List[Dict[str, Any]]] = None
    external_integrations: Optional[List[Dict[str, Any]]] = None
    trust_boundaries: Optional[List[Dict[str, Any]]] = None


@dataclass
class DataFlow:
    """Represents a data flow between components."""

    source: str
    target: str
    type: str
    category: str
    protocol: str
    port: Optional[int] = None
    direction: str = "bidirectional"
    data_classification: str = "unknown"
    encryption: bool = False
    authentication: str = "unknown"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExternalIntegration:
    """Represents an external system integration."""

    name: str
    type: str
    category: str
    protocol: str
    endpoint: Optional[str] = None
    authentication: str = "unknown"
    data_classification: str = "unknown"
    criticality: str = "medium"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TrustBoundary:
    """Represents a trust boundary in the system."""

    name: str
    type: str
    category: str
    components: List[str]
    security_controls: List[str]
    threat_level: str = "medium"
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Pydantic Models for Agent Outputs


# Config Analysis Models
class ServiceDependency(BaseModel):
    service_name: str
    dependency_type: str
    connection_details: Dict[str, Any]
    trust_boundary: str
    confidence: float


class ExternalIntegrationInfo(BaseModel):
    integration_name: str
    integration_type: str
    provider: str
    service_name: str
    endpoints: List[str]
    data_sensitivity: str
    confidence: float


class NetworkConfig(BaseModel):
    component: str
    config_type: str
    listen_ports: List[int]
    upstream_services: List[str]
    security_features: List[str]
    confidence: float


class InfrastructureComponent(BaseModel):
    component_name: str
    component_type: str
    deployment_environment: str
    scaling_config: Optional[str] = None
    resource_limits: Optional[str] = None
    confidence: float


class TrustBoundaryInfo(BaseModel):
    boundary_name: str
    internal_components: List[str]
    external_components: List[str]
    security_controls: List[str]
    data_flows: List[str]
    confidence: float


class ConfigAnalysisResult(BaseModel):
    service_dependencies: List[ServiceDependency] = []
    external_integrations: List[ExternalIntegrationInfo] = []
    network_config: List[NetworkConfig] = []
    infrastructure_components: List[InfrastructureComponent] = []
    trust_boundaries: List[TrustBoundaryInfo] = []


# Service Dependency Models
class InternalService(BaseModel):
    service_name: str
    service_type: str
    communication_protocol: str
    endpoints: List[str]
    dependencies: List[str]
    health_check_endpoint: Optional[str] = None
    service_discovery_method: Optional[str] = None
    confidence: float


class DatabaseConnection(BaseModel):
    database_name: str
    database_type: str
    connection_details: Dict[str, Any]
    access_patterns: List[str]
    data_models: List[str]
    migration_strategy: Optional[str] = None
    backup_frequency: Optional[str] = None
    confidence: float


class MessageQueue(BaseModel):
    queue_name: str
    queue_type: str
    topics_channels: List[str]
    producers: List[str]
    consumers: List[str]
    message_patterns: List[str]
    dead_letter_queue: Optional[str] = None
    retention_policy: Optional[str] = None
    confidence: float


class CachingLayer(BaseModel):
    cache_name: str
    cache_type: str
    cache_strategy: str
    ttl_policy: Optional[str] = None
    eviction_policy: Optional[str] = None
    data_types_cached: List[str]
    cache_hit_ratio_target: Optional[str] = None
    confidence: float


class NetworkConfigService(BaseModel):
    component: str
    network_type: str
    routing_rules: List[str]
    upstream_services: List[str]
    downstream_services: List[str]
    traffic_policies: List[str]
    circuit_breaker: Optional[str] = None
    retry_policies: Optional[str] = None
    confidence: float


class ServiceDependencyResult(BaseModel):
    internal_services: List[InternalService] = []
    database_connections: List[DatabaseConnection] = []
    message_queues: List[MessageQueue] = []
    caching_layers: List[CachingLayer] = []
    network_config: List[NetworkConfigService] = []


# External Integration Models
class CloudService(BaseModel):
    provider: str
    service_name: str
    service_type: str
    region: Optional[str] = None
    configuration: Optional[str] = None
    data_classification: Optional[str] = None
    cost_implications: Optional[str] = None
    vendor_lock_in_risk: Optional[str] = None
    confidence: float


class ThirdPartyAPI(BaseModel):
    api_name: str
    provider: str
    api_type: str
    base_url: Optional[str] = None
    endpoints_used: List[str]
    authentication_method: Optional[str] = None
    rate_limits: Optional[str] = None
    data_exchanged: List[str]
    business_purpose: Optional[str] = None
    sla_requirements: Optional[str] = None
    confidence: float


class SaaSIntegration(BaseModel):
    service_name: str
    vendor: str
    integration_type: str
    data_sync_pattern: Optional[str] = None
    data_flow_direction: Optional[str] = None
    business_function: Optional[str] = None
    compliance_requirements: List[str]
    data_residency: Optional[str] = None
    confidence: float


class PaymentIntegration(BaseModel):
    provider: str
    integration_method: str
    payment_methods: List[str]
    currencies_supported: List[str]
    pci_compliance_level: Optional[str] = None
    fraud_detection: Optional[str] = None
    webhook_endpoints: List[str]
    confidence: float


class ExternalDataSource(BaseModel):
    source_name: str
    data_type: str
    access_method: str
    update_frequency: Optional[str] = None
    data_format: Optional[str] = None
    data_volume: Optional[str] = None
    reliability_requirements: Optional[str] = None
    backup_strategy: Optional[str] = None
    confidence: float


class ExternalIntegrationResult(BaseModel):
    cloud_services: List[CloudService] = []
    third_party_apis: List[ThirdPartyAPI] = []
    saas_integrations: List[SaaSIntegration] = []
    payment_integrations: List[PaymentIntegration] = []
    external_data_sources: List[ExternalDataSource] = []


# Security Boundary Models
class TokenManagement(BaseModel):
    token_type: str
    expiration_time: Optional[str] = None
    refresh_strategy: Optional[str] = None
    revocation_mechanism: Optional[str] = None


class MultiFactor(BaseModel):
    enabled: bool
    factors: List[str]


class AuthenticationMechanism(BaseModel):
    auth_type: str
    implementation: Optional[str] = None
    identity_provider: Optional[str] = None
    token_management: Optional[TokenManagement] = None
    multi_factor: Optional[MultiFactor] = None
    session_management: Optional[str] = None
    confidence: float


class RolePermission(BaseModel):
    role_name: str
    permissions: List[str]
    resource_access: List[str]
    inheritance: Optional[str] = None


class AuthorizationModel(BaseModel):
    model_type: str
    roles_permissions: List[RolePermission]
    policy_engine: Optional[str] = None
    access_control_lists: List[str]
    attribute_sources: List[str]
    enforcement_points: List[str]
    confidence: float


class TrustBoundaryAnalysis(BaseModel):
    boundary_name: str
    boundary_type: str
    internal_components: List[str]
    external_components: List[str]
    crossing_mechanisms: List[str]
    security_controls: List[str]
    data_classification_levels: List[str]
    threat_vectors: List[str]
    monitoring_controls: List[str]
    confidence: float


class NetworkSecurity(BaseModel):
    control_type: str
    implementation: Optional[str] = None
    rules_policies: List[str]
    protected_resources: List[str]
    allowed_traffic: List[str]
    blocked_traffic: List[str]
    logging_monitoring: Optional[str] = None
    incident_response: Optional[str] = None
    confidence: float


class KeyManagement(BaseModel):
    key_storage: str
    key_rotation: Optional[str] = None
    key_escrow: Optional[str] = None
    access_controls: List[str]


class EncryptionControl(BaseModel):
    encryption_scope: str
    algorithm: str
    key_size: Optional[str] = None
    key_management: Optional[KeyManagement] = None
    implementation_details: Optional[str] = None
    compliance_standards: List[str]
    confidence: float


class AuditLog(BaseModel):
    log_type: str
    log_format: str
    logged_events: List[str]
    retention_policy: Optional[str] = None
    log_aggregation: Optional[str] = None
    monitoring_alerting: Optional[str] = None
    compliance_reporting: Optional[str] = None
    confidence: float


class SecurityBoundaryResult(BaseModel):
    authentication_mechanisms: List[AuthenticationMechanism] = []
    authorization_models: List[AuthorizationModel] = []
    trust_boundaries: List[TrustBoundaryAnalysis] = []
    network_security: List[NetworkSecurity] = []
    encryption_controls: List[EncryptionControl] = []
    audit_logging: List[AuditLog] = []


# Synthesis Models
class ArchitectureOverview(BaseModel):
    system_type: str
    deployment_model: str
    architecture_pattern: str
    primary_technologies: List[str]
    description: str


class Interface(BaseModel):
    interface_type: str
    protocol: str
    authentication: str
    encryption: str


class Component(BaseModel):
    component_name: str
    component_type: str
    responsibilities: List[str]
    technologies: List[str]
    interfaces: List[Interface]
    trust_zone: str


class DataFlowInfo(BaseModel):
    flow_id: str
    source: str
    destination: str
    data_type: str
    protocol: str
    encryption: str
    authentication: str
    trust_boundary_crossing: bool
    security_implications: List[str]


class DataFlowDiagram(BaseModel):
    description: str
    flows: List[DataFlowInfo]


class ExternalIntegrationSynthesis(BaseModel):
    integration_name: str
    provider: str
    service_type: str
    data_exchanged: List[str]
    trust_level: str
    security_controls: List[str]
    attack_vectors: List[str]


class TrustBoundarySynthesis(BaseModel):
    boundary_name: str
    description: str
    internal_zone: str
    external_zone: str
    crossing_points: List[str]
    security_controls: List[str]
    data_classifications: List[str]
    threats: List[str]


class EntryPoint(BaseModel):
    entry_point: str
    access_method: str
    authentication: str
    authorization: str
    network_exposure: str
    attack_vectors: List[str]


class DataStore(BaseModel):
    store_name: str
    store_type: str
    data_sensitivity: str
    access_controls: List[str]
    encryption: str
    backup_strategy: str
    threats: List[str]


class AttackSurface(BaseModel):
    entry_points: List[EntryPoint]
    data_stores: List[DataStore]


class SecurityAssessment(BaseModel):
    overall_risk: str
    key_concerns: List[str]
    recommendations: List[str]
    compliance_implications: List[str]


class SynthesisResult(BaseModel):
    architecture_overview: ArchitectureOverview
    component_map: List[Component]
    data_flow_diagram: DataFlowDiagram
    external_integrations: List[ExternalIntegrationSynthesis]
    trust_boundaries: List[TrustBoundarySynthesis]
    attack_surface: AttackSurface
    security_assessment: SecurityAssessment
    architecture_diagram_description: str
