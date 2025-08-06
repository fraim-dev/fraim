# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Discovery Orchestrator Workflow

Orchestrates Infrastructure Discovery and API Interface Discovery workflows to
create a complete system architecture view including data flows, trust boundaries,
and component relationships.
"""

import asyncio
import os
from typing import Any, Dict, List

from fraim.config import Config
from fraim.core.workflows import Workflow
from fraim.workflows.registry import workflow
from fraim.workflows.utils.write_json_output import write_json_output
from .types import ArchitectureDiscoveryInput, ComponentDiscoveryResults
from .component_discovery import ComponentDiscoveryExecutor
from .data_flow_analyzer import DataFlowAnalyzer
from .external_integrations import ExternalIntegrationAnalyzer
from .trust_boundaries import TrustBoundaryAnalyzer
from .diagram_generator import ArchitectureDiagramGenerator
from .synthesis_utils import SynthesisUtils


@workflow("architecture_discovery")
class ArchitectureDiscoveryOrchestrator(Workflow[ArchitectureDiscoveryInput, Dict[str, Any]]):
    """
    Orchestrates Infrastructure Discovery and API Interface Discovery to create
    comprehensive system architecture analysis.

    This workflow:
    1. Runs infrastructure_discovery and api_interface_discovery in parallel
    2. Synthesizes results into complete architecture view
    3. Maps data flows between discovered components
    4. Identifies trust boundaries and external integrations
    5. Generates architecture diagrams
    6. Writes category-based output files for each analysis type
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config
        self.results = ComponentDiscoveryResults()

        # Initialize analyzer components
        self.component_executor = ComponentDiscoveryExecutor(config)
        self.data_flow_analyzer = DataFlowAnalyzer(config)
        self.external_analyzer = ExternalIntegrationAnalyzer(config)
        self.trust_analyzer = TrustBoundaryAnalyzer(config)
        self.diagram_generator = ArchitectureDiagramGenerator(config)
        self.synthesis_utils = SynthesisUtils(config)

    async def workflow(self, input: ArchitectureDiscoveryInput) -> Dict[str, Any]:
        """Main orchestrator workflow executing component discovery and synthesis."""

        try:
            self.config.logger.info(
                "Starting Architecture Discovery Orchestrator")

            # Phase 1: Parallel Component Discovery
            await self._execute_component_discovery(input)

            # Phase 2: Architecture Synthesis
            await self._execute_architecture_synthesis(input)

            # Phase 3: Write Category-Based Output Files
            await self._write_category_files(input)

            self.config.logger.info(
                "Architecture Discovery Orchestrator completed successfully")

            # Return structured architecture results
            return {
                "architecture_diagram": self.results.architecture_diagram,
                "data_flows": self.results.data_flows or [],
                "external_integrations": self.results.external_integrations or [],
                "trust_boundaries": self.results.trust_boundaries or [],
                "components": {
                    "infrastructure": self.results.infrastructure or {},
                    "api_interfaces": self.results.api_interfaces or {}
                },
                "metadata": self.synthesis_utils.create_metadata_summary(
                    self.results, input.diagram_format
                )
            }

        except Exception as e:
            self.config.logger.error(
                f"Architecture Discovery Orchestrator failed: {str(e)}")
            raise

    async def _execute_component_discovery(self, input: ArchitectureDiscoveryInput) -> None:
        """Execute Phase 1: Parallel Component Discovery."""

        self.config.logger.info("Starting Phase 1: Component Discovery")

        # Use the component discovery executor
        self.results = await self.component_executor.execute_component_discovery(input)

        self.config.logger.info("Phase 1: Component Discovery completed")

    async def _execute_architecture_synthesis(self, input: ArchitectureDiscoveryInput) -> None:
        """Execute Phase 2: Architecture Synthesis."""

        self.config.logger.info("Starting Phase 2: Architecture Synthesis")

        # Synthesize component results using analyzer classes
        synthesis_tasks = [
            self._synthesize_architecture_diagram(input),
            self._synthesize_data_flows(input),
            self._synthesize_external_integrations(input),
            self._synthesize_trust_boundaries(input)
        ]

        await asyncio.gather(*synthesis_tasks)

        self.config.logger.info("Phase 2: Architecture Synthesis completed")

    async def _synthesize_architecture_diagram(self, input: ArchitectureDiscoveryInput) -> None:
        """Synthesize complete architecture diagram from component discoveries."""

        self.config.logger.info("Synthesizing architecture diagram")

        try:
            # Use the diagram generator
            self.results.architecture_diagram = await self.diagram_generator.generate_diagram(
                self.results, input.diagram_format
            )

            self.config.logger.info("Architecture diagram synthesis completed")

        except Exception as e:
            self.config.logger.error(
                f"Architecture diagram synthesis failed: {str(e)}")
            self.results.architecture_diagram = f"Architecture diagram generation failed: {str(e)}"

    async def _synthesize_data_flows(self, input: ArchitectureDiscoveryInput) -> None:
        """Synthesize data flows between discovered components."""

        if not input.include_data_flows:
            self.results.data_flows = []
            return

        self.config.logger.info("Synthesizing data flows")

        try:
            # Use the data flow analyzer
            self.results.data_flows = await self.data_flow_analyzer.analyze_data_flows(self.results)

            self.config.logger.info(
                f"Synthesized {len(self.results.data_flows)} data flows")

        except Exception as e:
            self.config.logger.error(f"Data flow synthesis failed: {str(e)}")
            self.results.data_flows = []

    async def _synthesize_external_integrations(self, input: ArchitectureDiscoveryInput) -> None:
        """Synthesize external system integrations."""

        self.config.logger.info("Synthesizing external integrations")

        try:
            # Use the external integration analyzer
            self.results.external_integrations = await self.external_analyzer.analyze_external_integrations(self.results)

            self.config.logger.info(
                f"Synthesized {len(self.results.external_integrations)} external integrations"
            )

        except Exception as e:
            self.config.logger.error(
                f"External integration synthesis failed: {str(e)}")
            self.results.external_integrations = []

    async def _synthesize_trust_boundaries(self, input: ArchitectureDiscoveryInput) -> None:
        """Synthesize trust boundaries from component analysis."""

        self.config.logger.info(
            f"Trust boundary synthesis called. include_trust_boundaries={input.include_trust_boundaries}")

        if not input.include_trust_boundaries:
            self.config.logger.info("Trust boundaries disabled, skipping")
            self.results.trust_boundaries = []
            return

        self.config.logger.info("Synthesizing trust boundaries")

        try:
            # Use the trust boundary analyzer
            self.results.trust_boundaries = await self.trust_analyzer.analyze_trust_boundaries(self.results)

            self.config.logger.info(
                f"Synthesized {len(self.results.trust_boundaries)} trust boundaries"
            )

        except Exception as e:
            self.config.logger.error(
                f"Trust boundary synthesis failed: {str(e)}")
            import traceback
            self.config.logger.error(f"Traceback: {traceback.format_exc()}")
            self.results.trust_boundaries = []

    async def _write_category_files(self, input: ArchitectureDiscoveryInput) -> None:
        """Write separate files for each analyzed category."""

        self.config.logger.info(
            "Starting file writing for analyzed categories")

        try:
            # Write architecture diagram (text file)
            if self.results.architecture_diagram:
                await self._write_architecture_diagram(input.diagram_format)

            # Write data flows (JSON)
            if self.results.data_flows:
                await self._write_data_flows()

            # Write external integrations (JSON)
            if self.results.external_integrations:
                await self._write_external_integrations()

            # Write trust boundaries (JSON)
            if self.results.trust_boundaries:
                await self._write_trust_boundaries()

            # Write component data (JSON)
            await self._write_component_data()

            # Write metadata summary (JSON)
            await self._write_metadata_summary(input.diagram_format)

            self.config.logger.info("Successfully wrote all category files")

        except Exception as e:
            self.config.logger.error(f"Error writing category files: {str(e)}")
            import traceback
            self.config.logger.error(f"Traceback: {traceback.format_exc()}")

    async def _write_architecture_diagram(self, diagram_format: str) -> None:
        """Write architecture diagram to file."""
        try:
            output_dir = getattr(self.config, "output_dir", None)
            if not output_dir:
                self.config.logger.warning(
                    "No output directory configured, skipping diagram file")
                return

            os.makedirs(output_dir, exist_ok=True)

            # Determine file extension based on format
            ext = {"mermaid": "mmd", "plantuml": "puml",
                   "text": "txt"}.get(diagram_format, "txt")
            filename = f"architecture_diagram.{ext}"
            file_path = os.path.join(output_dir, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.results.architecture_diagram or "")

            self.config.logger.info(
                f"Architecture diagram written to {file_path}")

        except Exception as e:
            self.config.logger.error(
                f"Error writing architecture diagram: {str(e)}")

    async def _write_data_flows(self) -> None:
        """Write data flows to JSON file."""
        try:
            flows = self.results.data_flows or []
            data_flows_data = {
                "data_flows": flows,
                "summary": {
                    "total_flows": len(flows),
                    "flow_types": list(set(flow.get("type", "unknown") for flow in flows)),
                    "protocols": list(set(flow.get("protocol", "unknown") for flow in flows))
                }
            }

            write_json_output(
                results=data_flows_data,
                workflow_name="architecture_discovery_data_flows",
                config=self.config,
                include_timestamp=True
            )

        except Exception as e:
            self.config.logger.error(f"Error writing data flows: {str(e)}")

    async def _write_external_integrations(self) -> None:
        """Write external integrations to JSON file."""
        try:
            integrations = self.results.external_integrations or []
            integrations_data = {
                "external_integrations": integrations,
                "summary": {
                    "total_integrations": len(integrations),
                    "integration_types": list(set(integ.get("type", "unknown") for integ in integrations)),
                    "providers": list(set(integ.get("metadata", {}).get("provider", "unknown") for integ in integrations))
                }
            }

            write_json_output(
                results=integrations_data,
                workflow_name="architecture_discovery_external_integrations",
                config=self.config,
                include_timestamp=True
            )

        except Exception as e:
            self.config.logger.error(
                f"Error writing external integrations: {str(e)}")

    async def _write_trust_boundaries(self) -> None:
        """Write trust boundaries to JSON file."""
        try:
            boundaries = self.results.trust_boundaries or []
            boundaries_data = {
                "trust_boundaries": boundaries,
                "summary": {
                    "total_boundaries": len(boundaries),
                    "boundary_types": list(set(boundary.get("type", "unknown") for boundary in boundaries)),
                    "threat_levels": list(set(boundary.get("threat_level", "unknown") for boundary in boundaries)),
                    "categories": list(set(boundary.get("category", "unknown") for boundary in boundaries))
                }
            }

            write_json_output(
                results=boundaries_data,
                workflow_name="architecture_discovery_trust_boundaries",
                config=self.config,
                include_timestamp=True
            )

        except Exception as e:
            self.config.logger.error(
                f"Error writing trust boundaries: {str(e)}")

    async def _write_component_data(self) -> None:
        """Write component discovery data to JSON file."""
        try:
            components_data = {
                "components": {
                    "infrastructure": self.results.infrastructure or {},
                    "api_interfaces": self.results.api_interfaces or {}
                },
                "summary": {
                    "infrastructure_available": self.results.infrastructure is not None,
                    "api_interfaces_available": self.results.api_interfaces is not None,
                    "total_components": self.synthesis_utils.count_discovered_components(self.results),
                    "unique_components": self.synthesis_utils.extract_unique_components(self.results)
                }
            }

            write_json_output(
                results=components_data,
                workflow_name="architecture_discovery_components",
                config=self.config,
                include_timestamp=True
            )

        except Exception as e:
            self.config.logger.error(f"Error writing component data: {str(e)}")

    async def _write_metadata_summary(self, diagram_format: str) -> None:
        """Write metadata summary to JSON file."""
        try:
            metadata = self.synthesis_utils.create_metadata_summary(
                self.results, diagram_format
            )

            # Add additional file writing metadata
            metadata.update({
                "files_written": {
                    "architecture_diagram": self.results.architecture_diagram is not None,
                    "data_flows": self.results.data_flows is not None and len(self.results.data_flows) > 0,
                    "external_integrations": self.results.external_integrations is not None and len(self.results.external_integrations) > 0,
                    "trust_boundaries": self.results.trust_boundaries is not None and len(self.results.trust_boundaries) > 0,
                    "components": True  # Always written
                }
            })

            write_json_output(
                results=metadata,
                workflow_name="architecture_discovery_metadata",
                config=self.config,
                include_timestamp=True
            )

        except Exception as e:
            self.config.logger.error(
                f"Error writing metadata summary: {str(e)}")
