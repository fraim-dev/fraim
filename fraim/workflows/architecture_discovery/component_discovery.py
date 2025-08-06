# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Component Discovery Executor

Handles execution of infrastructure discovery and API interface discovery
workflows with proper error handling and result processing.
"""

import asyncio
from typing import Any, Dict, List
from fraim.config import Config
from .types import ArchitectureDiscoveryInput, ComponentDiscoveryResults


class ComponentDiscoveryExecutor:
    """Executes component discovery workflows in parallel."""

    def __init__(self, config: Config):
        self.config = config

    async def execute_component_discovery(self, input: ArchitectureDiscoveryInput) -> ComponentDiscoveryResults:
        """Execute infrastructure and API discovery workflows in parallel."""
        self.config.logger.info("Starting parallel component discovery")

        results = ComponentDiscoveryResults()

        # Run infrastructure and API discovery in parallel
        tasks = [
            self._execute_infrastructure_discovery(input),
            self._execute_api_interface_discovery(input)
        ]

        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
        self._process_component_discovery_results(parallel_results, results)

        self.config.logger.info("Parallel component discovery completed")
        return results

    async def _execute_infrastructure_discovery(self, input: ArchitectureDiscoveryInput) -> Dict[str, Any]:
        """Execute infrastructure_discovery workflow to map deployment topology."""

        self.config.logger.info("Executing infrastructure discovery workflow")

        try:
            # Import the infrastructure discovery workflow
            from fraim.workflows.infrastructure_discovery.workflow import (
                InfrastructureDiscoveryWorkflow,
                InfrastructureDiscoveryInput
            )

            # Create infrastructure discovery input
            infra_input = InfrastructureDiscoveryInput(
                config=self.config,
                location=input.location,
                chunk_size=input.chunk_size,
                limit=input.limit,
                globs=input.globs,
                max_concurrent_chunks=input.max_concurrent_chunks
            )

            # Execute the infrastructure discovery workflow
            infra_workflow = InfrastructureDiscoveryWorkflow(self.config)
            results = await infra_workflow.workflow(infra_input)

            self.config.logger.info(
                "Infrastructure discovery workflow completed")
            return results

        except ImportError as e:
            self.config.logger.warning(
                f"Infrastructure discovery workflow not yet implemented: {str(e)}")
            return {
                "deployment_topology": {},
                "resource_dependencies": [],
                "network_architecture": {},
                "infrastructure_components": [],
                "error": "Infrastructure discovery workflow not yet implemented"
            }
        except Exception as e:
            self.config.logger.error(
                f"Infrastructure discovery workflow failed: {str(e)}")
            # Return default structure to prevent downstream failures
            return {
                "deployment_topology": {},
                "resource_dependencies": [],
                "network_architecture": {},
                "infrastructure_components": [],
                "error": f"Infrastructure discovery failed: {str(e)}"
            }

    async def _execute_api_interface_discovery(self, input: ArchitectureDiscoveryInput) -> Dict[str, Any]:
        """Execute api_interface_discovery workflow to map service contracts."""

        self.config.logger.info("Executing API interface discovery workflow")

        try:
            # Import the API interface discovery workflow
            from fraim.workflows.api_interface_discovery.workflow import (
                ApiInterfaceDiscoveryWorkflow as APIInterfaceDiscoveryWorkflow,
                ApiInterfaceDiscoveryInput as APIInterfaceDiscoveryInput
            )

            # Create API interface discovery input
            api_input = APIInterfaceDiscoveryInput(
                config=self.config,
                location=input.location,
                chunk_size=input.chunk_size,
                limit=input.limit,
                globs=input.globs,
                max_concurrent_chunks=input.max_concurrent_chunks
            )

            # Execute the API interface discovery workflow
            api_workflow = APIInterfaceDiscoveryWorkflow(self.config)
            results = await api_workflow.workflow(api_input)

            self.config.logger.info(
                "API interface discovery workflow completed")
            return results

        except ImportError as e:
            self.config.logger.warning(
                f"API interface discovery workflow not yet implemented: {str(e)}")
            return {
                "api_endpoints": [],
                "service_contracts": [],
                "inter_service_communication": [],
                "external_api_dependencies": [],
                "error": "API interface discovery workflow not yet implemented"
            }
        except Exception as e:
            self.config.logger.error(
                f"API interface discovery workflow failed: {str(e)}")
            # Return default structure to prevent downstream failures
            return {
                "api_endpoints": [],
                "service_contracts": [],
                "inter_service_communication": [],
                "external_api_dependencies": [],
                "error": f"API interface discovery failed: {str(e)}"
            }

    def _process_component_discovery_results(self, parallel_results: List[Any], results: ComponentDiscoveryResults) -> None:
        """Process and store component discovery results."""

        self.config.logger.info("Processing component discovery results")

        try:
            # Process infrastructure discovery results
            if len(parallel_results) > 0:
                infra_result = parallel_results[0]
                if not isinstance(infra_result, Exception):
                    results.infrastructure = infra_result
                    self.config.logger.info(
                        "Stored infrastructure discovery results")
                else:
                    self.config.logger.error(
                        f"Infrastructure discovery failed: {infra_result}")
                    results.infrastructure = {"error": str(infra_result)}

            # Process API interface discovery results
            if len(parallel_results) > 1:
                api_result = parallel_results[1]
                if not isinstance(api_result, Exception):
                    results.api_interfaces = api_result
                    self.config.logger.info(
                        "Stored API interface discovery results")
                else:
                    self.config.logger.error(
                        f"API interface discovery failed: {api_result}")
                    results.api_interfaces = {"error": str(api_result)}

        except Exception as e:
            self.config.logger.error(
                f"Error processing component discovery results: {str(e)}")
            # Set defaults to prevent downstream failures
            if results.infrastructure is None:
                results.infrastructure = {}
            if results.api_interfaces is None:
                results.api_interfaces = {}

    def get_discovery_summary(self, results: ComponentDiscoveryResults) -> Dict[str, Any]:
        """Generate a summary of component discovery results."""
        summary = {
            "infrastructure_discovered": results.infrastructure is not None,
            "api_interfaces_discovered": results.api_interfaces is not None,
            "infrastructure_error": None,
            "api_error": None,
            "component_counts": {}
        }

        # Check for infrastructure errors and count components
        if results.infrastructure:
            if "error" in results.infrastructure:
                summary["infrastructure_error"] = results.infrastructure["error"]
            else:
                summary["component_counts"]["infrastructure"] = self._count_infrastructure_components(
                    results.infrastructure)

        # Check for API errors and count components
        if results.api_interfaces:
            if "error" in results.api_interfaces:
                summary["api_error"] = results.api_interfaces["error"]
            else:
                summary["component_counts"]["api"] = self._count_api_components(
                    results.api_interfaces)

        return summary

    def _count_infrastructure_components(self, infrastructure: Dict[str, Any]) -> Dict[str, int]:
        """Count infrastructure components by type."""
        counts = {}

        if "deployment_topology" in infrastructure:
            topology = infrastructure["deployment_topology"]
            for component_type, instances in topology.items():
                if isinstance(instances, list):
                    counts[component_type] = len(instances)
                elif isinstance(instances, dict):
                    counts[component_type] = 1

        if "resource_dependencies" in infrastructure:
            counts["resource_dependencies"] = len(
                infrastructure["resource_dependencies"])

        if "network_architecture" in infrastructure:
            network = infrastructure["network_architecture"]
            if isinstance(network, dict):
                if "subnets" in network:
                    counts["subnets"] = len(network["subnets"])
                if "security_groups" in network:
                    counts["security_groups"] = len(network["security_groups"])

        return counts

    def _count_api_components(self, api_interfaces: Dict[str, Any]) -> Dict[str, int]:
        """Count API components by type."""
        counts = {}

        for component_type in ["api_endpoints", "service_contracts", "inter_service_communication", "external_api_dependencies"]:
            if component_type in api_interfaces:
                components = api_interfaces[component_type]
                if isinstance(components, list):
                    counts[component_type] = len(components)

        return counts
