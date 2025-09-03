# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Component Consolidation

Handles consolidation, merging, and semantic grouping of infrastructure components,
containers, and deployment environments from multiple analysis chunks.
"""

from typing import Any

from fraim.config import Config

from .component_filters import apply_infrastructure_filters
from .types import ContainerConfig, DeploymentEnvironment, InfrastructureAnalysisResult, InfrastructureComponent


class InfrastructureConsolidator:
    """Handles consolidation of infrastructure analysis results."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def consolidate(self, chunk_results: list[InfrastructureAnalysisResult]) -> InfrastructureAnalysisResult:
        """Consolidate infrastructure components using rule-based merging and semantic grouping."""
        self.config.logger.info(f"Starting consolidation for {len(chunk_results)} chunks")

        # Collect all items from chunks
        all_containers = []
        all_components = []
        all_environments = []

        for result in chunk_results:
            all_containers.extend(result.container_configs)
            all_components.extend(result.infrastructure_components)
            all_environments.extend(result.deployment_environments)

        self.config.logger.debug(
            f"Collected {len(all_containers)} containers, {len(all_components)} components, "
            f"{len(all_environments)} environments before consolidation"
        )

        # Apply consolidation with semantic grouping
        final_containers = self._merge_containers(all_containers)
        final_components = self._merge_components(all_components)
        final_environments = self._merge_environments(all_environments)

        # Apply post-processing filters to improve component quality
        final_components = apply_infrastructure_filters(final_components)

        self.config.logger.info(
            f"Consolidation completed: "
            f"{len(all_containers)} → {len(final_containers)} containers, "
            f"{len(all_components)} → {len(final_components)} components, "
            f"{len(all_environments)} → {len(final_environments)} environments"
        )

        return InfrastructureAnalysisResult(
            container_configs=final_containers,
            infrastructure_components=final_components,
            deployment_environments=final_environments,
        )

    def _merge_containers(self, containers: list[ContainerConfig]) -> list[ContainerConfig]:
        """Merge containers with normalization for any container runtime."""
        if not containers:
            return []

        merged: dict[tuple[str, str], ContainerConfig] = {}

        for container in containers:
            # Normalize container name and base image for better matching
            normalized_name = container.container_name.lower().strip()
            normalized_image = container.base_image.lower().strip()
            key = (normalized_name, normalized_image)

            if key in merged:
                existing = merged[key]
                # Merge environment variables (avoid duplicates)
                existing_env_names = {env.name for env in existing.environment_variables}
                for env_var in container.environment_variables:
                    if env_var.name not in existing_env_names:
                        existing.environment_variables.append(env_var)

                # Merge exposed ports (avoid duplicates)
                existing_ports = set(existing.exposed_ports)
                for port in container.exposed_ports:
                    if port not in existing_ports:
                        existing.exposed_ports.append(port)

                # Merge volume mounts (avoid duplicates)
                existing_volumes = set(existing.volume_mounts)
                for volume in container.volume_mounts:
                    if volume not in existing_volumes:
                        existing.volume_mounts.append(volume)

                # Use higher confidence
                existing.confidence = max(existing.confidence, container.confidence)
            else:
                merged[key] = container

        self.config.logger.debug(f"Container consolidation: {len(containers)} → {len(merged)} containers")
        return list(merged.values())

    def _merge_components(self, components: list[InfrastructureComponent]) -> list[InfrastructureComponent]:
        """Merge components with semantic grouping for any cloud/infrastructure provider."""
        if not components:
            return []

        # Apply semantic grouping first
        semantically_grouped = self._apply_semantic_grouping(components)

        # Then apply standard consolidation
        merged: dict[tuple[str, str], InfrastructureComponent] = {}

        for component in semantically_grouped:
            # Create semantic key for better matching
            semantic_key = self._create_semantic_component_key(component)

            if semantic_key in merged:
                existing = merged[semantic_key]
                # Keep component with higher confidence or more detailed configuration
                if component.confidence > existing.confidence or (
                    component.confidence == existing.confidence
                    and len(component.configuration) > len(existing.configuration)
                ):
                    merged[semantic_key] = component
            else:
                merged[semantic_key] = component

        self.config.logger.debug(f"Component consolidation: {len(components)} → {len(merged)} components")
        return list(merged.values())

    def _merge_environments(self, environments: list[DeploymentEnvironment]) -> list[DeploymentEnvironment]:
        """Merge environments with normalization for any deployment pattern."""
        if not environments:
            return []

        merged: dict[str, DeploymentEnvironment] = {}

        for environment in environments:
            # Normalize environment names (dev/development, prod/production, etc.)
            normalized_name = self._normalize_environment_name(environment.name)

            if normalized_name in merged:
                existing = merged[normalized_name]

                # Merge network policies
                existing_policies = set(existing.network_policies)
                for policy in environment.network_policies:
                    if policy not in existing_policies:
                        existing.network_policies.append(policy)

                # Merge configurations (prefer non-null values)
                if not existing.namespace and environment.namespace:
                    existing.namespace = environment.namespace
                if not existing.resource_quotas and environment.resource_quotas:
                    existing.resource_quotas = environment.resource_quotas
                if not existing.secrets_management and environment.secrets_management:
                    existing.secrets_management = environment.secrets_management
                if not existing.ingress_config and environment.ingress_config:
                    existing.ingress_config = environment.ingress_config
                if not existing.monitoring_config and environment.monitoring_config:
                    existing.monitoring_config = environment.monitoring_config

                # Use higher confidence
                existing.confidence = max(existing.confidence, environment.confidence)
            else:
                # Use normalized name for consistency
                environment.name = normalized_name
                merged[normalized_name] = environment

        self.config.logger.debug(f"Environment consolidation: {len(environments)} → {len(merged)} environments")
        return list(merged.values())

    def _apply_semantic_grouping(self, components: list[InfrastructureComponent]) -> list[InfrastructureComponent]:
        """Apply semantic grouping to consolidate related components (API routes, databases, etc.)."""
        if not components:
            return []

        # Group components by semantic patterns
        api_route_groups: dict[str, list[InfrastructureComponent]] = {}
        database_groups: dict[str, list[InfrastructureComponent]] = {}
        other_components: list[InfrastructureComponent] = []

        for component in components:
            if self._is_api_route_component(component):
                service_name = self._extract_api_service_name(component)
                if service_name not in api_route_groups:
                    api_route_groups[service_name] = []
                api_route_groups[service_name].append(component)
            elif self._is_database_component(component):
                db_name = self._extract_database_name(component)
                if db_name not in database_groups:
                    database_groups[db_name] = []
                database_groups[db_name].append(component)
            else:
                other_components.append(component)

        # Consolidate API route groups
        consolidated = []
        for service_name, routes in api_route_groups.items():
            consolidated_route = self._consolidate_api_routes(service_name, routes)
            consolidated.append(consolidated_route)

        # Consolidate database groups
        for db_name, dbs in database_groups.items():
            consolidated_db = self._consolidate_databases(db_name, dbs)
            consolidated.append(consolidated_db)

        # Add other components as-is
        consolidated.extend(other_components)

        self.config.logger.debug(
            f"Semantic grouping: {len(components)} → {len(consolidated)} components "
            f"(consolidated {len(api_route_groups)} API services, {len(database_groups)} databases)"
        )

        return consolidated

    def _is_api_route_component(self, component: InfrastructureComponent) -> bool:
        """Check if component represents an API route that should be grouped."""
        name_lower = component.name.lower()
        return (
            "route:" in name_lower
            or "api route" in name_lower
            or (
                "api" in name_lower
                and any(method in name_lower for method in ["get", "post", "put", "delete", "patch", "options"])
            )
        )

    def _is_database_component(self, component: InfrastructureComponent) -> bool:
        """Check if component represents a database that should be grouped."""
        name_lower = component.name.lower()
        type_lower = component.type.lower()
        return type_lower == "database" or any(
            db in name_lower for db in ["mysql", "postgres", "mariadb", "mongodb", "redis", "dynamodb", "rds"]
        )

    def _extract_api_service_name(self, component: InfrastructureComponent) -> str:
        """Extract service name from API route component."""
        name = component.name

        # Pattern: "Service API Route: METHOD /path" -> "Service API"
        if " API Route:" in name:
            return name.split(" API Route:")[0] + " API"

        # Pattern: "Service Route: METHOD /path" -> "Service API"
        if " Route:" in name:
            return name.split(" Route:")[0] + " API"

        # Pattern: "API Gateway V2 Route" -> "API Gateway"
        if "Route" in name and "API" in name:
            # Extract service part before "Route"
            parts = name.split()
            service_parts = []
            for part in parts:
                if "route" not in part.lower():
                    service_parts.append(part)
                else:
                    break
            return " ".join(service_parts)

        # Fallback: use first part of name
        return name.split()[0] + " API" if name else "Unknown API"

    def _extract_database_name(self, component: InfrastructureComponent) -> str:
        """Extract database name for grouping."""
        name_lower = component.name.lower()

        # Common database patterns
        for db_type in ["mysql", "postgres", "mariadb", "mongodb", "redis", "dynamodb"]:
            if db_type in name_lower:
                return f"{db_type.title()} Database"

        # RDS pattern
        if "rds" in name_lower:
            return "RDS Database"

        # Fallback
        return "Database Service"

    def _consolidate_api_routes(
        self, service_name: str, routes: list[InfrastructureComponent]
    ) -> InfrastructureComponent:
        """Consolidate multiple API routes into a single API Gateway component."""
        if len(routes) == 1:
            # Single route - just update name to be more generic
            route = routes[0]
            route.name = service_name
            route.type = "api_gateway"
            return route

        # Multiple routes - create consolidated component
        # Use the route with highest confidence as base
        base_route = max(routes, key=lambda r: r.confidence)

        # Extract all HTTP methods and paths
        methods_and_paths = []
        for route in routes:
            if ":" in route.name:
                method_path = route.name.split(":", 1)[1].strip()
                if method_path:
                    methods_and_paths.append(method_path)

        # Create consolidated configuration
        config_parts = [base_route.configuration]
        if methods_and_paths:
            config_parts.append(f"Routes: {', '.join(sorted(set(methods_and_paths)))}")

        consolidated = InfrastructureComponent(
            name=service_name,
            type="api_gateway",
            provider=base_route.provider,
            service_name=base_route.service_name,
            configuration="; ".join(config_parts),
            discovery_method=base_route.discovery_method,
            file_source=base_route.file_source,
            availability_zone=base_route.availability_zone,
            backup_strategy=base_route.backup_strategy,
            monitoring=base_route.monitoring,
            confidence=max(r.confidence for r in routes),
        )

        return consolidated

    def _consolidate_databases(self, db_name: str, databases: list[InfrastructureComponent]) -> InfrastructureComponent:
        """Consolidate multiple database components."""
        if len(databases) == 1:
            db = databases[0]
            db.name = db_name
            return db

        # Multiple databases - merge configurations
        base_db = max(databases, key=lambda d: d.confidence)

        # Merge configurations
        configs = [db.configuration for db in databases if db.configuration.strip()]
        # Preserve order, remove duplicates
        unique_configs = list(dict.fromkeys(configs))

        consolidated = InfrastructureComponent(
            name=db_name,
            type="database",
            provider=base_db.provider,
            service_name=base_db.service_name,
            configuration="; ".join(unique_configs),
            discovery_method=base_db.discovery_method,
            file_source=base_db.file_source,
            availability_zone=base_db.availability_zone,
            backup_strategy=base_db.backup_strategy,
            monitoring=base_db.monitoring,
            confidence=max(d.confidence for d in databases),
        )

        return consolidated

    def _create_semantic_component_key(self, component: InfrastructureComponent) -> tuple[str, str]:
        """Create a semantic key for component consolidation with provider normalization."""
        # Normalize component name and type
        normalized_name = component.name.lower().strip()
        normalized_type = self._normalize_component_type(component.type, component.provider)

        # Handle special cases for better grouping
        if normalized_type == "api_gateway":
            # Group all API gateway components by service
            if "api" in normalized_name:
                # Extract service name for API components
                service_name = normalized_name.split("api")[0].strip()
                return (f"{service_name}_api", normalized_type)

        return (normalized_name, normalized_type)

    def _normalize_component_type(self, component_type: str, provider: str) -> str:
        """Normalize component types across different providers."""
        type_lower = component_type.lower().strip()
        provider_lower = provider.lower().strip() if provider else ""

        # Provider-agnostic type mappings
        TYPE_MAPPINGS = {
            # API/Gateway types
            "api_gateway": ["api_gateway", "apigateway", "api gateway", "app_gateway", "application_gateway"],
            "proxy": ["proxy", "reverse_proxy", "load_balancer", "alb", "nlb", "elb", "lb"],
            # Storage types
            "storage": ["storage", "s3", "blob", "object_storage", "bucket", "gcs", "azure_storage"],
            "database": ["database", "db", "rds", "sql", "nosql", "dynamodb", "cosmosdb", "cloudsql"],
            "cache": ["cache", "redis", "memcached", "elasticache"],
            # Network types
            "network": ["vpc", "vnet", "subnet", "network", "networking"],
            "dns": ["dns", "route53", "dns_zone", "private_dns"],
            "cdn": ["cdn", "cloudfront", "azurefront", "cloudflare"],
            # Compute types
            "compute": ["ec2", "vm", "instance", "compute", "ecs", "fargate", "aci"],
            "container": ["container", "docker", "k8s", "kubernetes", "ecs", "aci"],
            # Security types
            "security": ["iam", "rbac", "security_group", "nsg", "firewall", "kms", "key_vault"],
            "secrets": ["secrets", "parameter_store", "key_vault", "secret_manager"],
            # Monitoring types
            "monitoring": ["cloudwatch", "monitor", "logging", "metrics", "alerts", "application_insights"],
            # Message/Queue types
            "queue": ["sqs", "queue", "servicebus", "pubsub", "sns", "topic"],
        }

        # Find matching normalized type
        for normalized, variants in TYPE_MAPPINGS.items():
            if type_lower in variants:
                return normalized

        # Provider-specific mappings
        if provider_lower == "aws":
            aws_mappings = {
                "lambda": "compute",
                "apigatewayv2": "api_gateway",
                "rds": "database",
                "elasticache": "cache",
                "route53": "dns",
            }
            if type_lower in aws_mappings:
                return aws_mappings[type_lower]

        elif provider_lower == "azure":
            azure_mappings = {
                "functions": "compute",
                "app_service": "compute",
                "sql_database": "database",
                "cosmos_db": "database",
            }
            if type_lower in azure_mappings:
                return azure_mappings[type_lower]

        elif provider_lower == "gcp":
            gcp_mappings = {"cloud_functions": "compute", "cloud_sql": "database", "cloud_storage": "storage"}
            if type_lower in gcp_mappings:
                return gcp_mappings[type_lower]

        # Return original if no mapping found
        return type_lower

    def _normalize_environment_name(self, env_name: str) -> str:
        """Normalize environment names for consistent grouping."""
        name_lower = env_name.lower().strip()

        # Common environment name mappings
        ENV_MAPPINGS = {
            "development": ["dev", "develop", "development"],
            "staging": ["stage", "staging", "stg", "test", "testing"],
            "production": ["prod", "production", "live"],
            "preview": ["preview", "pre", "demo"],
            "qa": ["qa", "quality", "qassurance"],
        }

        for normalized, variants in ENV_MAPPINGS.items():
            if name_lower in variants:
                return normalized

        # Return original if no mapping found
        return name_lower
