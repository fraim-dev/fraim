# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Client Discovery Service

Implements hybrid client discovery to replace the hardcoded "client" problem
in data flow analysis. Uses actual discovered components where they exist, 
generates smart placeholders where they don't.
"""

from typing import Any, Dict, List, Optional, Set
from fraim.config import Config
from .types import UnifiedComponent


class ClientDiscoveryService:
    """Hybrid client discovery service to identify API consumers."""

    def __init__(self, config: Config):
        self.config = config
        self._client_cache: Dict[str, List[UnifiedComponent]] = {}
        self._generated_clients: List[UnifiedComponent] = []

    def discover_api_clients(self,
                             api_component: UnifiedComponent,
                             all_components: List[UnifiedComponent]) -> List[UnifiedComponent]:
        """
        Main entry point: Discover clients for an API service using hybrid approach.

        Uses actual discovered components where they exist, generates smart 
        placeholders where they don't.
        """
        # Check cache first
        cache_key = api_component.component_id
        if cache_key in self._client_cache:
            return self._client_cache[cache_key]

        clients = []

        # Tier 1: Find explicit client components
        explicit_clients = self._find_explicit_clients(
            api_component, all_components)
        if explicit_clients:
            clients.extend(explicit_clients)
            self.config.logger.debug(
                f"Found {len(explicit_clients)} explicit clients for {api_component.component_name}")

        # Tier 2: Find pattern-based clients
        pattern_clients = self._find_pattern_clients(
            api_component, all_components)
        if pattern_clients:
            clients.extend(pattern_clients)
            self.config.logger.debug(
                f"Found {len(pattern_clients)} pattern-based clients for {api_component.component_name}")

        # Tier 3: Generate smart placeholder clients if none found
        if not clients:
            generated_clients = self._generate_smart_clients(api_component)
            clients.extend(generated_clients)
            self._generated_clients.extend(generated_clients)
            self.config.logger.info(
                f"Generated {len(generated_clients)} placeholder clients for {api_component.component_name}")

        # Cache the results
        self._client_cache[cache_key] = clients
        return clients

    def _find_explicit_clients(self,
                               api_component: UnifiedComponent,
                               components: List[UnifiedComponent]) -> List[UnifiedComponent]:
        """Find components that explicitly depend on this API service."""
        clients = []

        for comp in components:
            # Skip self-references
            if comp.component_id == api_component.component_id:
                continue

            # Check explicit dependencies
            if api_component.component_id in comp.dependencies:
                clients.append(comp)
                continue

            # Check if component name appears in dependencies
            api_name_variations = self._get_name_variations(api_component)
            for dep in comp.dependencies:
                if any(variation.lower() in str(dep).lower() for variation in api_name_variations):
                    clients.append(comp)
                    break

        return clients

    def _find_pattern_clients(self,
                              api_component: UnifiedComponent,
                              components: List[UnifiedComponent]) -> List[UnifiedComponent]:
        """Find clients based on naming patterns and component types."""
        clients = []
        api_name_base = self._extract_service_base_name(
            api_component.component_name)

        for comp in components:
            if comp.component_id == api_component.component_id:
                continue

            comp_name = comp.component_name.lower()

            # Frontend/UI components that could consume this API
            if self._is_frontend_component(comp):
                # Check if frontend matches API service domain
                if api_name_base in comp_name:
                    clients.append(comp)
                    continue

                # Generic frontend components can consume auth APIs
                if any(term in api_component.component_name.lower()
                       for term in ["auth", "login", "user", "profile"]):
                    clients.append(comp)
                    continue

            # Mobile app components
            if self._is_mobile_component(comp) and api_name_base in comp_name:
                clients.append(comp)
                continue

            # Other services that might consume this API
            if (comp.component_type == "service" and
                    comp.component_id != api_component.component_id):
                # Services can consume other services' APIs
                if self._services_likely_connected(comp, api_component):
                    clients.append(comp)

        return clients

    def _generate_smart_clients(self, api_component: UnifiedComponent) -> List[UnifiedComponent]:
        """Generate contextually appropriate client placeholders."""
        clients = []
        api_name_base = self._extract_service_base_name(
            api_component.component_name)

        # Analyze API characteristics to determine appropriate client types
        api_characteristics = self._analyze_api_characteristics(api_component)

        # Generate clients based on API type and endpoints
        for characteristic in api_characteristics:
            client = self._create_client_for_characteristic(
                characteristic, api_component, api_name_base)
            if client is not None:
                clients.append(client)

        # Always ensure at least one generic client exists
        if not clients:
            clients.append(self._create_generic_client(
                api_component, api_name_base))

        return clients

    def _analyze_api_characteristics(self, api_component: UnifiedComponent) -> List[str]:
        """Analyze API component to determine what types of clients it likely serves."""
        characteristics = set()

        api_name = api_component.component_name.lower()

        # Analyze component name
        if any(term in api_name for term in ["auth", "login", "user", "profile", "account"]):
            characteristics.update(["web_client", "mobile_client"])
        elif any(term in api_name for term in ["admin", "dashboard", "management"]):
            characteristics.add("admin_client")
        elif any(term in api_name for term in ["public", "external", "partner"]):
            characteristics.add("external_client")
        elif any(term in api_name for term in ["webhook", "callback", "notification"]):
            characteristics.add("service_client")

        # Analyze API endpoints if available
        if api_component.api_interfaces:
            for api_interface in api_component.api_interfaces:
                endpoints = api_interface.get("endpoints", [])
                for endpoint in endpoints:
                    path = endpoint.get("endpoint_path", "").lower()

                    if any(term in path for term in ["/admin", "/dashboard", "/manage"]):
                        characteristics.add("admin_client")
                    elif any(term in path for term in ["/auth", "/login", "/register"]):
                        characteristics.update(["web_client", "mobile_client"])
                    elif any(term in path for term in ["/api/v", "/public"]):
                        characteristics.add("external_client")
                    elif any(term in path for term in ["/webhook", "/callback"]):
                        characteristics.add("service_client")

        # Default fallback
        if not characteristics:
            characteristics.add("generic_client")

        return list(characteristics)

    def _create_client_for_characteristic(self,
                                          characteristic: str,
                                          api_component: UnifiedComponent,
                                          api_name_base: str) -> Optional[UnifiedComponent]:
        """Create a client component for a specific characteristic."""

        client_configs = {
            "web_client": {
                "name": f"Web Application ({api_name_base})",
                "type": "frontend",
                "description": f"Web frontend client for {api_component.component_name}"
            },
            "mobile_client": {
                "name": f"Mobile Application ({api_name_base})",
                "type": "mobile",
                "description": f"Mobile app client for {api_component.component_name}"
            },
            "admin_client": {
                "name": f"Admin Dashboard ({api_name_base})",
                "type": "admin",
                "description": f"Administrative interface for {api_component.component_name}"
            },
            "external_client": {
                "name": f"External Service ({api_name_base})",
                "type": "external",
                "description": f"External system consuming {api_component.component_name}"
            },
            "service_client": {
                "name": f"Internal Service ({api_name_base})",
                "type": "service",
                "description": f"Internal service consuming {api_component.component_name}"
            },
            "generic_client": {
                "name": f"Client Application ({api_name_base})",
                "type": "client",
                "description": f"Client application for {api_component.component_name}"
            }
        }

        if characteristic not in client_configs:
            return None

        config = client_configs[characteristic]

        return UnifiedComponent(
            component_id=f"{characteristic}_{api_component.component_id}",
            component_name=config["name"],
            component_type=config["type"],
            description=config["description"],
            confidence=0.7,  # Generated clients have medium confidence
            # Client depends on the API
            dependencies=[api_component.component_id],
            protocols=["https", "http"],
            metadata={
                "generated": True,
                "generated_for_api": api_component.component_id,
                "generation_reason": f"No explicit clients found for {api_component.component_name}",
                "client_characteristic": characteristic
            }
        )

    def _create_generic_client(self, api_component: UnifiedComponent, api_name_base: str) -> UnifiedComponent:
        """Create a generic fallback client."""
        return UnifiedComponent(
            component_id=f"client_{api_component.component_id}",
            component_name=f"Client Application ({api_name_base})",
            component_type="client",
            description=f"Generic client application for {api_component.component_name}",
            confidence=0.6,  # Lower confidence for generic fallback
            dependencies=[api_component.component_id],
            protocols=["https", "http"],
            metadata={
                "generated": True,
                "generated_for_api": api_component.component_id,
                "generation_reason": f"Fallback client for {api_component.component_name}",
                "client_characteristic": "generic"
            }
        )

    def _is_frontend_component(self, component: UnifiedComponent) -> bool:
        """Check if component is a frontend/UI component."""
        name = component.component_name.lower()
        type_name = component.component_type.lower()

        frontend_indicators = [
            "frontend", "ui", "web", "react", "vue", "angular",
            "nextjs", "webapp", "website", "portal", "dashboard"
        ]

        return (any(indicator in name for indicator in frontend_indicators) or
                type_name in ["frontend", "ui", "web", "webapp"])

    def _is_mobile_component(self, component: UnifiedComponent) -> bool:
        """Check if component is a mobile app component."""
        name = component.component_name.lower()
        type_name = component.component_type.lower()

        mobile_indicators = [
            "mobile", "android", "ios", "app", "native", "react-native", "flutter"
        ]

        return (any(indicator in name for indicator in mobile_indicators) or
                type_name in ["mobile", "app"])

    def _services_likely_connected(self, service1: UnifiedComponent, service2: UnifiedComponent) -> bool:
        """Heuristic to determine if two services are likely connected."""
        # Services in the same domain/context often communicate
        name1_words = set(service1.component_name.lower().split())
        name2_words = set(service2.component_name.lower().split())

        # Check for shared domain words
        common_words = name1_words.intersection(name2_words)
        domain_words = {"user", "auth", "payment", "order",
                        "product", "inventory", "notification"}

        if common_words.intersection(domain_words):
            return True

        # Check if service1 might be a gateway/proxy for service2
        if any(term in service1.component_name.lower() for term in ["gateway", "proxy", "router", "lb", "balancer"]):
            return True

        return False

    def _get_name_variations(self, component: UnifiedComponent) -> List[str]:
        """Get different name variations for a component."""
        variations = [component.component_name]

        # Add component ID
        variations.append(component.component_id)

        # Add name without common suffixes
        name_base = component.component_name.lower()
        for suffix in [" service", " api", " application", " app"]:
            if name_base.endswith(suffix):
                variations.append(name_base[:-len(suffix)].strip())

        # Add hyphenated and underscore versions
        base_name = component.component_name.replace(" ", "-").lower()
        variations.extend([base_name, base_name.replace("-", "_")])

        return variations

    def _extract_service_base_name(self, service_name: str) -> str:
        """Extract the base name from a service name."""
        # Remove common service suffixes
        base_name = service_name.lower()
        suffixes_to_remove = [
            " api service", " service", " api", " application", " app",
            " server", " backend", " frontend", " client"
        ]

        for suffix in suffixes_to_remove:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)].strip()
                break

        # Remove common prefixes
        prefixes_to_remove = ["api ", "service "]
        for prefix in prefixes_to_remove:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):].strip()
                break

        return base_name.replace(" ", "_").replace("-", "_")

    def get_generated_clients(self) -> List[UnifiedComponent]:
        """Get all generated client components for integration into component list."""
        return self._generated_clients

    def clear_cache(self) -> None:
        """Clear the client discovery cache."""
        self._client_cache.clear()
        self._generated_clients.clear()

    def get_client_summary(self) -> Dict[str, Any]:
        """Get a summary of client discovery results."""
        total_apis_processed = len(self._client_cache)
        total_clients_discovered = sum(len(clients)
                                       for clients in self._client_cache.values())
        generated_clients_count = len(self._generated_clients)
        explicit_clients_count = total_clients_discovered - generated_clients_count

        return {
            "total_apis_processed": total_apis_processed,
            "total_clients_discovered": total_clients_discovered,
            "explicit_clients_found": explicit_clients_count,
            "generated_clients_created": generated_clients_count,
            "cache_size": len(self._client_cache)
        }
