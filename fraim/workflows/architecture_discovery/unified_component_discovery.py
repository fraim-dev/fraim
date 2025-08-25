# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Unified Component Discovery Executor

Combines infrastructure discovery and API interface discovery into a unified
component identification approach that creates a complete system component view.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fraim.config import Config

from .types import ArchitectureDiscoveryInput, ComponentDiscoveryResults, UnifiedComponent, UnifiedComponentDiscovery


class UnifiedComponentDiscoveryExecutor:
    """Executes unified component discovery that combines infrastructure and API analysis."""

    def __init__(self, config: Config):
        self.config = config

    async def execute_unified_component_discovery(
        self,
        input: ArchitectureDiscoveryInput,
        infrastructure_data: Optional[Dict[str, Any]] = None,
        api_interfaces_data: Optional[Dict[str, Any]] = None
    ) -> ComponentDiscoveryResults:
        """Execute unified component discovery using provided infrastructure and API data."""
        self.config.logger.info("Starting unified component discovery")

        results = ComponentDiscoveryResults()

        # Store the provided data for backward compatibility
        results.infrastructure = infrastructure_data or {}
        results.api_interfaces = api_interfaces_data or {}

        # Transform the legacy data into unified components
        unified_discovery = await self._discover_unified_components(infrastructure_data or {}, api_interfaces_data or {})

        results.unified_components = unified_discovery

        self.config.logger.info(
            f"Unified component discovery completed. Found {len(unified_discovery.components)} components")
        return results

    async def _discover_unified_components(self, infrastructure: Dict[str, Any], api_interfaces: Dict[str, Any]) -> UnifiedComponentDiscovery:
        """Transform and combine infrastructure and API discovery results into unified components."""

        self.config.logger.info(
            "Unifying infrastructure and API discovery results into unified components")

        unified_components = []

        # Process infrastructure components
        if infrastructure and "infrastructure_components" in infrastructure:
            for infra_comp in infrastructure["infrastructure_components"]:
                unified_comp = self._create_unified_component_from_infrastructure(
                    infra_comp)
                unified_components.append(unified_comp)

        # Process container configurations as service components
        if infrastructure and "container_configs" in infrastructure:
            for container in infrastructure["container_configs"]:
                unified_comp = self._create_unified_component_from_container(
                    container)
                unified_components.append(unified_comp)

        # Process API interfaces - group by service/component
        if api_interfaces and "rest_endpoints" in api_interfaces:
            api_components = self._group_api_endpoints_by_component(
                api_interfaces)
            for api_comp in api_components:
                unified_components.append(api_comp)

        # Discover relationships between components
        component_relationships = self._discover_component_relationships(
            unified_components, infrastructure, api_interfaces)

        # Update component dependencies based on discovered relationships
        self._update_component_dependencies(
            unified_components, component_relationships)

        # Calculate overall confidence
        total_confidence = 0.0
        if unified_components:
            total_confidence = sum(
                comp.confidence for comp in unified_components) / len(unified_components)

        # Create summary
        summary = self._create_discovery_summary(
            unified_components, infrastructure, api_interfaces)

        return UnifiedComponentDiscovery(
            components=unified_components,
            component_relationships=component_relationships,
            summary=summary,
            confidence=total_confidence
        )


    def _create_unified_component_from_infrastructure(self, infra_comp: Dict[str, Any]) -> UnifiedComponent:
        """Create a unified component from an infrastructure component."""

        return UnifiedComponent(
            component_id=f"infra_{infra_comp.get('name', 'unknown')}",
            component_name=infra_comp.get(
                'name', 'Unknown Infrastructure Component'),
            # database, cache, queue, load_balancer, etc.
            component_type=infra_comp.get('type', 'other'),
            description=f"{infra_comp.get('service_name', '')} {infra_comp.get('type', '')} component".strip(
            ),
            infrastructure_details={
                'provider': infra_comp.get('provider'),
                'service_name': infra_comp.get('service_name'),
                'configuration': infra_comp.get('configuration'),
                'availability_zone': infra_comp.get('availability_zone'),
                'backup_strategy': infra_comp.get('backup_strategy'),
                'monitoring': infra_comp.get('monitoring')
            },
            exposed_ports=[],  # Infrastructure components don't typically expose ports directly
            protocols=[],
            endpoints=[],
            confidence=infra_comp.get('confidence', 0.0),
            source_files=[],  # Would need to track this from discovery process
            metadata={'source': 'infrastructure_discovery',
                      'original_data': infra_comp}
        )

    def _create_unified_component_from_container(self, container: Dict[str, Any]) -> UnifiedComponent:
        """Create a unified component from a container configuration."""

        return UnifiedComponent(
            component_id=f"service_{container.get('container_name', 'unknown')}",
            component_name=container.get('container_name', 'Unknown Service'),
            component_type='service',  # Container configs typically represent services
            description=f"Service running in container {container.get('container_name', '')}",
            deployment_info={
                'base_image': container.get('base_image'),
                'environment_variables': container.get('environment_variables', []),
                'volume_mounts': container.get('volume_mounts', []),
                'resource_limits': container.get('resource_limits', {})
            },
            exposed_ports=container.get('exposed_ports', []),
            protocols=['http', 'https'] if container.get(
                'exposed_ports') else [],
            confidence=container.get('confidence', 0.0),
            source_files=[],  # Would need to track this from discovery process
            metadata={'source': 'infrastructure_discovery',
                      'original_data': container}
        )

    def _group_api_endpoints_by_component(self, api_interfaces: Dict[str, Any]) -> List[UnifiedComponent]:
        """Group API endpoints by their likely component/service and create unified components."""

        components = []

        # Group REST endpoints by path prefix or service
        if "rest_endpoints" in api_interfaces:
            endpoint_groups = self._group_endpoints_by_service(
                api_interfaces["rest_endpoints"])

            for service_name, endpoints in endpoint_groups.items():
                protocols = ['http', 'https']
                # Common defaults, could be improved with actual port detection
                exposed_ports = [80, 443]

                # Collect all endpoint paths
                endpoint_paths = [ep.get('endpoint_path', '')
                                  for ep in endpoints]

                component = UnifiedComponent(
                    component_id=f"api_{service_name}",
                    component_name=f"{service_name} API Service",
                    component_type='service',
                    description=f"API service handling {len(endpoints)} endpoints",
                    api_interfaces=[{
                        'type': 'rest',
                        'endpoints': endpoints
                    }],
                    exposed_ports=exposed_ports,
                    protocols=protocols,
                    endpoints=endpoint_paths,
                    confidence=sum(ep.get('confidence', 0.0)
                                   for ep in endpoints) / len(endpoints) if endpoints else 0.0,
                    source_files=[],
                    metadata={'source': 'api_interface_discovery',
                              'endpoint_count': len(endpoints)}
                )
                components.append(component)

        return components

    def _group_endpoints_by_service(self, endpoints: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group REST endpoints by their likely service/component."""

        groups: Dict[str, List[Dict[str, Any]]] = {}

        for endpoint in endpoints:
            path = endpoint.get('endpoint_path', '')

            # Simple grouping by first path segment
            service_name = 'api'  # default
            if path.startswith('/'):
                parts = path.split('/')[1:2]  # Get first path segment
                if parts:
                    service_name = parts[0] or 'api'

            if service_name not in groups:
                groups[service_name] = []
            groups[service_name].append(endpoint)

        return groups

    def _discover_component_relationships(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any], api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover relationships between unified components."""

        relationships: List[Dict[str, Any]] = []

        # 1. Database connections between services and databases
        relationships.extend(self._discover_database_relationships(
            components, infrastructure))

        # 2. API calls between services
        relationships.extend(self._discover_api_relationships(
            components, api_interfaces))

        # 3. Message queue producers/consumers
        relationships.extend(self._discover_message_queue_relationships(
            components, infrastructure))

        # 4. Load balancer -> service relationships
        relationships.extend(self._discover_load_balancer_relationships(
            components, infrastructure))

        # 5. Pattern-based relationship inference for common architectural patterns
        relationships.extend(self._discover_pattern_based_relationships(
            components, infrastructure, api_interfaces))

        self.config.logger.info(
            f"Discovered {len(relationships)} component relationships")
        return relationships

    def _discover_database_relationships(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover database connection relationships between services and databases."""
        relationships = []

        # First try the expected data structure (for backward compatibility)
        if infrastructure and "database_connections" in infrastructure:
            for db_conn in infrastructure["database_connections"]:
                db_name = db_conn.get("database_name", "").lower()

                # Find the database component
                db_component = None
                for comp in components:
                    if (comp.component_type == "database" and
                        (db_name in comp.component_name.lower() or
                         db_name in str(comp.infrastructure_details or {}).lower())):
                        db_component = comp
                        break

                if db_component:
                    # Look for services that connect to this database
                    connecting_services = []

                    # Check environment variables and connection details for references
                    for comp in components:
                        if comp.component_type == "service":
                            env_vars = comp.deployment_info.get(
                                "environment_variables", []) if comp.deployment_info else []
                            env_str = " ".join(str(var)
                                               for var in env_vars).lower()

                            if (db_name in env_str or
                                    any(db_name in str(detail).lower() for detail in (comp.infrastructure_details or {}).values())):
                                connecting_services.append(comp)

                    # Create relationships
                    for service_comp in connecting_services:
                        relationships.append({
                            "type": "database_connection",
                            "source": service_comp.component_id,
                            "target": db_component.component_id,
                            "direction": "outbound",
                            "protocol": db_conn.get("database_type", "unknown"),
                            "metadata": {
                                "connection_details": db_conn.get("connection_details", {}),
                                "access_patterns": db_conn.get("access_patterns", []),
                                "confidence": db_conn.get("confidence", 0.7)
                            }
                        })

        # New logic: Infer database relationships from container configs and environment variables
        else:
            # Get all database-type components
            db_components = [
                comp for comp in components if comp.component_type in ["database", "cache"]]
            service_components = [
                comp for comp in components if comp.component_type == "service"]

            for db_comp in db_components:
                db_name = db_comp.component_name.lower()

                # Look for services that likely connect to this database
                for service_comp in service_components:
                    should_connect = False
                    connection_evidence = []

                    # Check environment variables for database references
                    if service_comp.deployment_info:
                        env_vars = service_comp.deployment_info.get(
                            "environment_variables", [])
                        for var in env_vars:
                            if isinstance(var, dict):
                                var_name = var.get("name", "").lower()
                                var_value = str(var.get("value", "")).lower()

                                # Look for database connection patterns
                                if any(db_term in var_name for db_term in [db_name, "database", "db"]):
                                    should_connect = True
                                    connection_evidence.append(
                                        f"env_var: {var_name}")

                                if db_name in var_value:
                                    should_connect = True
                                    connection_evidence.append(
                                        f"env_value: {var_name}")

                    # Infer common database connections based on naming patterns
                    if not should_connect:
                        # Common patterns: postgres service connects to postgres db, etc.
                        if any(db_term in service_comp.component_name.lower() for db_term in [db_name]):
                            should_connect = True
                            connection_evidence.append("naming_pattern")

                        # Services typically connect to redis for caching
                        if "redis" in db_name and service_comp.component_type == "service":
                            should_connect = True
                            connection_evidence.append("redis_cache_pattern")

                        # Services typically connect to main database
                        if "postgres" in db_name and service_comp.component_type == "service":
                            should_connect = True
                            connection_evidence.append("main_db_pattern")

                    if should_connect:
                        relationships.append({
                            "type": "database_connection",
                            "source": service_comp.component_id,
                            "target": db_comp.component_id,
                            "direction": "outbound",
                            "protocol": self._infer_database_protocol(db_comp),
                            "metadata": {
                                "connection_evidence": connection_evidence,
                                "confidence": 0.8 if "env_var" in str(connection_evidence) else 0.6
                            }
                        })

        return relationships

    def _discover_api_relationships(self, components: List[UnifiedComponent], api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover API call relationships between services."""
        relationships = []

        # First try the expected data structure (for backward compatibility)
        if api_interfaces and "inter_service_communication" in api_interfaces:
            for comm in api_interfaces["inter_service_communication"]:
                source_service = comm.get("source_service", "").lower()
                target_service = comm.get("target_service", "").lower()

                # Find corresponding components
                source_comp = None
                target_comp = None

                for comp in components:
                    comp_name_lower = comp.component_name.lower()
                    if source_service in comp_name_lower or comp_name_lower in source_service:
                        source_comp = comp
                    if target_service in comp_name_lower or comp_name_lower in target_service:
                        target_comp = comp

                if source_comp and target_comp and source_comp != target_comp:
                    relationships.append({
                        "type": "api_call",
                        "source": source_comp.component_id,
                        "target": target_comp.component_id,
                        "direction": "outbound",
                        "protocol": comm.get("protocol", "http"),
                        "metadata": {
                            "endpoints": comm.get("endpoints", []),
                            "methods": comm.get("methods", []),
                            "data_format": comm.get("data_format", "json"),
                            "confidence": comm.get("confidence", 0.8)
                        }
                    })

        # New logic: Infer API relationships from REST endpoints
        else:
            # Get all API service components
            api_services = [comp for comp in components if comp.api_interfaces and len(
                comp.api_interfaces) > 0]
            other_services = [comp for comp in components if comp.component_type == "service" and not (
                comp.api_interfaces and len(comp.api_interfaces) > 0)]

            # Create relationships from other services to API services
            for api_service in api_services:
                for client_service in other_services:
                    # Infer if client service likely calls this API
                    should_connect = False
                    connection_evidence = []

                    # Check environment variables for API references
                    if client_service.deployment_info:
                        env_vars = client_service.deployment_info.get(
                            "environment_variables", [])
                        for var in env_vars:
                            if isinstance(var, dict):
                                var_name = var.get("name", "").lower()
                                var_value = str(var.get("value", "")).lower()

                                # Look for API connection patterns
                                api_service_name = api_service.component_name.lower().replace(
                                    " api service", "").replace("_api", "").replace("-api", "")
                                if (api_service_name in var_name or api_service_name in var_value or
                                        any(api_term in var_name for api_term in ["api", "service", "endpoint", "url", "host"])):
                                    should_connect = True
                                    connection_evidence.append(
                                        f"env_var: {var_name}")

                    # Infer common API patterns
                    if not should_connect:
                        # Frontend services typically call backend APIs
                        if any(term in client_service.component_name.lower() for term in ["frontend", "ui", "web"]):
                            should_connect = True
                            connection_evidence.append(
                                "frontend_to_api_pattern")

                        # General service to API pattern
                        elif client_service.component_type == "service" and api_service.component_type == "service":
                            should_connect = True
                            connection_evidence.append(
                                "service_to_api_pattern")

                    if should_connect:
                        relationships.append({
                            "type": "api_call",
                            "source": client_service.component_id,
                            "target": api_service.component_id,
                            "direction": "outbound",
                            "protocol": "https",
                            "metadata": {
                                "connection_evidence": connection_evidence,
                                "endpoints": [ep for iface in (api_service.api_interfaces or []) for ep in iface.get("endpoints", [])],
                                "confidence": 0.6 if "env_var" in str(connection_evidence) else 0.4
                            }
                        })

            # Also create generic API to service relationships (API gateways to backend services)
            gateway_services = [comp for comp in components if any(term in comp.component_name.lower()
                                                                   for term in ["gateway", "proxy", "router", "load"])]
            backend_services = [comp for comp in components if comp.component_type == "service" and
                                not any(term in comp.component_name.lower() for term in ["gateway", "proxy", "ui", "frontend"])]

            for gateway in gateway_services:
                for backend in backend_services:
                    relationships.append({
                        "type": "gateway_to_service",
                        "source": gateway.component_id,
                        "target": backend.component_id,
                        "direction": "outbound",
                        "protocol": "http",
                        "metadata": {
                            "connection_evidence": ["gateway_pattern"],
                            "confidence": 0.5
                        }
                    })

        return relationships

    def _discover_message_queue_relationships(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover message queue producer/consumer relationships."""
        relationships = []

        # First try the expected data structure (for backward compatibility)
        if infrastructure and "message_queues" in infrastructure:
            for mq in infrastructure["message_queues"]:
                queue_name = mq.get("queue_name", "").lower()
                producers = mq.get("producers", [])
                consumers = mq.get("consumers", [])

                # Find the queue component
                queue_component = None
                for comp in components:
                    if (comp.component_type in ["queue", "message_queue"] and
                            queue_name in comp.component_name.lower()):
                        queue_component = comp
                        break

                if queue_component:
                    # Create producer relationships
                    for producer_name in producers:
                        producer_comp = None
                        for comp in components:
                            if producer_name.lower() in comp.component_name.lower():
                                producer_comp = comp
                                break

                        if producer_comp:
                            relationships.append({
                                "type": "message_producer",
                                "source": producer_comp.component_id,
                                "target": queue_component.component_id,
                                "direction": "outbound",
                                "protocol": mq.get("queue_type", "unknown"),
                                "metadata": {
                                    "topics_channels": mq.get("topics_channels", []),
                                    "message_patterns": mq.get("message_patterns", []),
                                    "confidence": mq.get("confidence", 0.8)
                                }
                            })

                    # Create consumer relationships
                    for consumer_name in consumers:
                        consumer_comp = None
                        for comp in components:
                            if consumer_name.lower() in comp.component_name.lower():
                                consumer_comp = comp
                                break

                        if consumer_comp:
                            relationships.append({
                                "type": "message_consumer",
                                "source": queue_component.component_id,
                                "target": consumer_comp.component_id,
                                "direction": "outbound",
                                "protocol": mq.get("queue_type", "unknown"),
                                "metadata": {
                                    "topics_channels": mq.get("topics_channels", []),
                                    "message_patterns": mq.get("message_patterns", []),
                                    "confidence": mq.get("confidence", 0.8)
                                }
                            })

        # New logic: Infer queue relationships from container configs
        else:
            # Get all queue-type components
            queue_components = [comp for comp in components if comp.component_type == "queue" or
                                any(queue_term in comp.component_name.lower() for queue_term in ["kafka", "rabbitmq", "activemq", "redis"])]
            service_components = [
                comp for comp in components if comp.component_type == "service"]

            for queue_comp in queue_components:
                queue_name = queue_comp.component_name.lower()

                # Look for services that likely connect to this queue
                for service_comp in service_components:
                    should_connect = False
                    connection_evidence = []

                    # Check environment variables for queue references
                    if service_comp.deployment_info:
                        env_vars = service_comp.deployment_info.get(
                            "environment_variables", [])
                        for var in env_vars:
                            if isinstance(var, dict):
                                var_name = var.get("name", "").lower()
                                var_value = str(var.get("value", "")).lower()

                                # Look for queue connection patterns
                                if any(queue_term in var_name for queue_term in [queue_name, "kafka", "rabbitmq", "queue", "messaging"]):
                                    should_connect = True
                                    connection_evidence.append(
                                        f"env_var: {var_name}")

                                if queue_name in var_value:
                                    should_connect = True
                                    connection_evidence.append(
                                        f"env_value: {var_name}")

                    # Infer common queue connections based on patterns
                    if not should_connect:
                        # Services typically connect to message queues for async processing
                        if any(queue_term in queue_name for queue_term in ["kafka", "rabbitmq"]) and service_comp.component_type == "service":
                            should_connect = True
                            connection_evidence.append("queue_pattern")

                    if should_connect:
                        # Create both producer and consumer relationships (bidirectional for simplicity)
                        relationships.append({
                            "type": "message_queue_connection",
                            "source": service_comp.component_id,
                            "target": queue_comp.component_id,
                            "direction": "bidirectional",
                            "protocol": self._infer_queue_protocol(queue_comp),
                            "metadata": {
                                "connection_evidence": connection_evidence,
                                "confidence": 0.7 if "env_var" in str(connection_evidence) else 0.5
                            }
                        })

        return relationships

    def _discover_load_balancer_relationships(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover load balancer to service relationships."""
        relationships = []

        # Look for network configurations that indicate load balancing
        if infrastructure and "network_config" in infrastructure:
            for net_config in infrastructure["network_config"]:
                component_name = net_config.get("component", "").lower()
                upstream_services = net_config.get("upstream_services", [])

                # Find the load balancer component
                lb_component = None
                for comp in components:
                    if (comp.component_type in ["load_balancer", "proxy", "gateway"] and
                        (component_name in comp.component_name.lower() or
                         comp.component_name.lower() in component_name)):
                        lb_component = comp
                        break

                if lb_component:
                    # Create relationships to upstream services
                    for upstream_service in upstream_services:
                        upstream_comp = None
                        for comp in components:
                            if (comp.component_type == "service" and
                                    upstream_service.lower() in comp.component_name.lower()):
                                upstream_comp = comp
                                break

                        if upstream_comp:
                            relationships.append({
                                "type": "load_balancer_backend",
                                "source": lb_component.component_id,
                                "target": upstream_comp.component_id,
                                "direction": "outbound",
                                "protocol": "http",
                                "metadata": {
                                    "routing_rules": net_config.get("routing_rules", []),
                                    "traffic_policies": net_config.get("traffic_policies", []),
                                    "health_check": net_config.get("circuit_breaker"),
                                    "confidence": net_config.get("confidence", 0.9)
                                }
                            })

        return relationships

    def _discover_pattern_based_relationships(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any], api_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover relationships based on common architectural patterns."""
        relationships = []

        self.config.logger.info(
            "Applying pattern-based relationship inference")

        # Categorize components for pattern matching
        services = [c for c in components if c.component_type == "service"]
        api_services = [
            c for c in services if c.api_interfaces and len(c.api_interfaces) > 0]
        databases = [c for c in components if c.component_type in [
            "database", "cache"]]
        queues = [c for c in components if c.component_type == "queue" or
                  any(q in c.component_name.lower() for q in ["kafka", "rabbitmq", "redis", "sqs", "activemq"])]
        storage = [c for c in components if c.component_type == "storage"]
        load_balancers = [c for c in components if c.component_type == "load_balancer" or
                          any(lb in c.component_name.lower() for lb in ["nginx", "haproxy", "traefik", "alb", "nlb"])]
        monitoring = [c for c in components if any(monitor in c.component_name.lower()
                                                   for monitor in ["prometheus", "grafana", "datadog", "newrelic", "elastic", "kibana", "logstash"])]

        # Pattern 1: API Gateway/Load Balancer -> Services
        relationships.extend(
            self._apply_gateway_to_service_pattern(load_balancers, services))

        # Pattern 2: Services -> Databases (every service needs data)
        relationships.extend(
            self._apply_service_to_database_pattern(services, databases))

        # Pattern 3: Services -> Queues (async communication)
        relationships.extend(
            self._apply_service_to_queue_pattern(services, queues))

        # Pattern 4: Services -> Storage (file/object storage)
        relationships.extend(
            self._apply_service_to_storage_pattern(services, storage))

        # Pattern 5: API Services -> Backend Services (service mesh)
        relationships.extend(
            self._apply_api_to_backend_pattern(api_services, services))

        # Pattern 6: Monitoring -> Everything (observability)
        relationships.extend(self._apply_monitoring_pattern(
            monitoring, services + api_services))

        # Pattern 7: Frontend -> Backend API pattern
        relationships.extend(
            self._apply_frontend_to_api_pattern(services, api_services))

        # Pattern 8: Microservices inter-communication
        relationships.extend(
            self._apply_microservices_communication_pattern(services, api_services))

        self.config.logger.info(
            f"Applied pattern-based inference, discovered {len(relationships)} additional relationships")
        return relationships

    def _apply_gateway_to_service_pattern(self, load_balancers: List[UnifiedComponent], services: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Gateway/Load Balancer -> Services"""
        relationships = []

        for lb in load_balancers:
            # Connect load balancers to application services (not infrastructure)
            for service in services:
                # Avoid connecting to other infrastructure-like services
                if not any(infra_term in service.component_name.lower()
                           for infra_term in ["monitor", "log", "metric", "trace", "admin"]):
                    relationships.append({
                        "type": "load_balancer_backend",
                        "source": lb.component_id,
                        "target": service.component_id,
                        "direction": "outbound",
                        "protocol": "http",
                        "metadata": {
                            "pattern": "gateway_to_service",
                            "confidence": 0.7,
                            "description": f"Load balancer {lb.component_name} routes traffic to service {service.component_name}"
                        }
                    })

        return relationships

    def _apply_service_to_database_pattern(self, services: List[UnifiedComponent], databases: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Services -> Databases (every service needs data storage)"""
        relationships: List[Dict[str, Any]] = []

        if not databases:
            return relationships

        # Primary database (usually postgres/mysql)
        primary_db = None
        cache_db = None

        for db in databases:
            db_name = db.component_name.lower()
            if any(primary in db_name for primary in ["postgres", "mysql", "oracle", "mssql"]):
                primary_db = db
                break
            elif "redis" in db_name:
                cache_db = db

        # If no primary found, use first database
        if not primary_db and databases:
            primary_db = databases[0]

        for service in services:
            # Connect to primary database
            if primary_db:
                relationships.append({
                    "type": "database_connection",
                    "source": service.component_id,
                    "target": primary_db.component_id,
                    "direction": "outbound",
                    "protocol": self._infer_database_protocol(primary_db),
                    "metadata": {
                        "pattern": "service_to_primary_db",
                        "confidence": 0.8,
                        "description": f"Service {service.component_name} stores data in {primary_db.component_name}"
                    }
                })

            # Connect to cache if available
            if cache_db:
                relationships.append({
                    "type": "cache_connection",
                    "source": service.component_id,
                    "target": cache_db.component_id,
                    "direction": "outbound",
                    "protocol": self._infer_database_protocol(cache_db),
                    "metadata": {
                        "pattern": "service_to_cache",
                        "confidence": 0.6,
                        "description": f"Service {service.component_name} uses {cache_db.component_name} for caching"
                    }
                })

        return relationships

    def _apply_service_to_queue_pattern(self, services: List[UnifiedComponent], queues: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Services -> Message Queues (async communication)"""
        relationships: List[Dict[str, Any]] = []

        if not queues:
            return relationships

        # Primary message queue (usually kafka or rabbitmq)
        primary_queue = None
        for queue in queues:
            queue_name = queue.component_name.lower()
            if any(mq in queue_name for mq in ["kafka", "rabbitmq", "activemq"]):
                primary_queue = queue
                break

        if not primary_queue and queues:
            primary_queue = queues[0]

        if primary_queue:
            for service in services:
                # Services both produce and consume messages
                relationships.extend([
                    {
                        "type": "message_producer",
                        "source": service.component_id,
                        "target": primary_queue.component_id,
                        "direction": "outbound",
                        "protocol": self._infer_queue_protocol(primary_queue),
                        "metadata": {
                            "pattern": "service_to_queue_producer",
                            "confidence": 0.5,
                            "description": f"Service {service.component_name} produces messages to {primary_queue.component_name}"
                        }
                    },
                    {
                        "type": "message_consumer",
                        "source": primary_queue.component_id,
                        "target": service.component_id,
                        "direction": "outbound",
                        "protocol": self._infer_queue_protocol(primary_queue),
                        "metadata": {
                            "pattern": "queue_to_service_consumer",
                            "confidence": 0.5,
                            "description": f"Service {service.component_name} consumes messages from {primary_queue.component_name}"
                        }
                    }
                ])

        return relationships

    def _apply_service_to_storage_pattern(self, services: List[UnifiedComponent], storage: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Services -> Storage (file/object storage)"""
        relationships: List[Dict[str, Any]] = []

        if not storage:
            return relationships

        # Primary object storage (usually S3)
        primary_storage = None
        for store in storage:
            store_name = store.component_name.lower()
            if any(s3_term in store_name for s3_term in ["s3", "bucket", "blob", "object"]):
                primary_storage = store
                break

        if not primary_storage and storage:
            primary_storage = storage[0]

        if primary_storage:
            # Only some services typically use object storage
            for service in services:
                service_name = service.component_name.lower()

                # Services that typically use file storage
                if any(storage_user in service_name for storage_user in
                       ["upload", "file", "media", "asset", "document", "image", "backup", "export", "import"]):
                    confidence = 0.8
                else:
                    confidence = 0.4  # Lower confidence for general services

                relationships.append({
                    "type": "storage_connection",
                    "source": service.component_id,
                    "target": primary_storage.component_id,
                    "direction": "outbound",
                    "protocol": "https",
                    "metadata": {
                        "pattern": "service_to_storage",
                        "confidence": confidence,
                        "description": f"Service {service.component_name} stores files in {primary_storage.component_name}"
                    }
                })

        return relationships

    def _apply_api_to_backend_pattern(self, api_services: List[UnifiedComponent], all_services: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: API Services -> Backend Services (service mesh communication)"""
        relationships = []

        # Backend services are those without API interfaces
        backend_services = [s for s in all_services if s not in api_services]

        for api_service in api_services:
            for backend_service in backend_services:
                # API services call backend services for business logic
                relationships.append({
                    "type": "service_call",
                    "source": api_service.component_id,
                    "target": backend_service.component_id,
                    "direction": "outbound",
                    "protocol": "http",
                    "metadata": {
                        "pattern": "api_to_backend",
                        "confidence": 0.5,
                        "description": f"API service {api_service.component_name} calls backend service {backend_service.component_name}"
                    }
                })

        return relationships

    def _apply_monitoring_pattern(self, monitoring: List[UnifiedComponent], services: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Monitoring -> Services (observability)"""
        relationships = []

        for monitor in monitoring:
            for service in services:
                relationships.append({
                    "type": "monitoring_connection",
                    "source": service.component_id,
                    "target": monitor.component_id,
                    "direction": "outbound",
                    "protocol": "http",
                    "metadata": {
                        "pattern": "service_to_monitoring",
                        "confidence": 0.6,
                        "description": f"Service {service.component_name} sends metrics/logs to {monitor.component_name}"
                    }
                })

        return relationships

    def _apply_frontend_to_api_pattern(self, services: List[UnifiedComponent], api_services: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Frontend -> Backend APIs"""
        relationships = []

        # Identify frontend services
        frontend_services = [s for s in services if any(frontend_term in s.component_name.lower()
                                                        for frontend_term in ["ui", "web", "frontend", "client", "app", "portal"])]

        for frontend in frontend_services:
            for api_service in api_services:
                # Frontend services call API services
                relationships.append({
                    "type": "api_call",
                    "source": frontend.component_id,
                    "target": api_service.component_id,
                    "direction": "outbound",
                    "protocol": "https",
                    "metadata": {
                        "pattern": "frontend_to_api",
                        "confidence": 0.7,
                        "description": f"Frontend {frontend.component_name} calls API {api_service.component_name}"
                    }
                })

        return relationships

    def _apply_microservices_communication_pattern(self, services: List[UnifiedComponent], api_services: List[UnifiedComponent]) -> List[Dict[str, Any]]:
        """Apply pattern: Microservices inter-service communication"""
        relationships = []

        # In microservices, services often communicate with each other
        for service1 in services:
            for service2 in api_services:
                if service1.component_id != service2.component_id:
                    # Look for naming patterns that suggest relationships
                    service1_name = service1.component_name.lower()
                    service2_name = service2.component_name.lower()

                    # Heuristic: services with related names likely communicate
                    confidence = self._calculate_service_relatedness(
                        service1_name, service2_name)

                    if confidence > 0.3:
                        relationships.append({
                            "type": "microservice_call",
                            "source": service1.component_id,
                            "target": service2.component_id,
                            "direction": "outbound",
                            "protocol": "http",
                            "metadata": {
                                "pattern": "microservice_communication",
                                "confidence": confidence,
                                "description": f"Microservice {service1.component_name} communicates with {service2.component_name}"
                            }
                        })

        return relationships

    def _calculate_service_relatedness(self, name1: str, name2: str) -> float:
        """Calculate how related two service names are for microservices communication."""

        # Domain-based relationships
        domains = {
            "user": ["auth", "profile", "account", "identity", "login"],
            "payment": ["billing", "invoice", "order", "transaction", "cart"],
            "inventory": ["product", "catalog", "stock", "item"],
            "communication": ["notification", "email", "sms", "message"],
            "analytics": ["metric", "report", "dashboard", "analytics", "tracking"]
        }

        # Check if services are in the same domain
        for domain, keywords in domains.items():
            in_domain1 = any(keyword in name1 for keyword in keywords)
            in_domain2 = any(keyword in name2 for keyword in keywords)
            if in_domain1 and in_domain2:
                return 0.6

        # Check for common words/tokens
        tokens1 = set(name1.replace("-", " ").replace("_", " ").split())
        tokens2 = set(name2.replace("-", " ").replace("_", " ").split())

        if tokens1 and tokens2:
            overlap = len(tokens1.intersection(tokens2))
            if overlap > 0:
                return 0.4 + (0.2 * overlap)

        return 0.0

    def _infer_queue_protocol(self, queue_component: UnifiedComponent) -> str:
        """Infer the queue protocol from component name and type."""
        queue_name = queue_component.component_name.lower()

        if "kafka" in queue_name:
            return "kafka"
        elif "rabbitmq" in queue_name:
            return "amqp"
        elif "activemq" in queue_name:
            return "jms"
        elif "redis" in queue_name:
            return "redis"
        elif "sqs" in queue_name:
            return "sqs"
        else:
            return "tcp"

    def _update_component_dependencies(self, components: List[UnifiedComponent], relationships: List[Dict[str, Any]]) -> None:
        """Update component dependencies based on discovered relationships."""

        # Create a mapping of component ID to component for quick lookup
        component_map = {comp.component_id: comp for comp in components}

        # Add dependencies based on relationships
        for relationship in relationships:
            source_id = relationship.get("source")
            target_id = relationship.get("target")

            if source_id in component_map and target_id in component_map:
                source_comp = component_map[source_id]
                target_comp = component_map[target_id]

                # Add target as a dependency of source
                if target_id not in source_comp.dependencies:
                    source_comp.dependencies.append(target_id)

                self.config.logger.debug(
                    f"Added dependency: {source_comp.component_name} -> {target_comp.component_name}")

    def _infer_database_protocol(self, db_component: UnifiedComponent) -> str:
        """Infer the database protocol from component name and type."""
        db_name = db_component.component_name.lower()

        if "postgres" in db_name:
            return "postgresql"
        elif "mysql" in db_name:
            return "mysql"
        elif "redis" in db_name:
            return "redis"
        elif "mongodb" in db_name or "mongo" in db_name:
            return "mongodb"
        elif "elasticsearch" in db_name:
            return "http"
        elif "cassandra" in db_name:
            return "cql"
        elif "oracle" in db_name:
            return "oracle"
        elif "mssql" in db_name or "sqlserver" in db_name:
            return "mssql"
        else:
            return "tcp"

    def _create_discovery_summary(self, components: List[UnifiedComponent], infrastructure: Dict[str, Any], api_interfaces: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of the unified component discovery results."""

        component_types = {}
        for comp in components:
            comp_type = comp.component_type
            if comp_type not in component_types:
                component_types[comp_type] = 0
            component_types[comp_type] += 1

        return {
            'total_components': len(components),
            'component_types': component_types,
            'sources': {
                'infrastructure_discovery': len([c for c in components if c.metadata and c.metadata.get('source') == 'infrastructure_discovery']),
                'api_interface_discovery': len([c for c in components if c.metadata and c.metadata.get('source') == 'api_interface_discovery'])
            },
            'infrastructure_analysis': {
                'files_analyzed': infrastructure.get('files_analyzed', 0),
                'confidence_score': infrastructure.get('confidence_score', 0.0)
            } if infrastructure else {},
            'api_analysis': {
                'files_analyzed': api_interfaces.get('files_analyzed', 0),
                'confidence_score': api_interfaces.get('confidence_score', 0.0)
            } if api_interfaces else {}
        }
