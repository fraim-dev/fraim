# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery Workflow

Analyzes source code and API specifications to identify API endpoints, protocols,
and interface contracts including REST, GraphQL, WebSocket endpoints, and data models.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, Workflow
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_json_output

from .file_patterns import API_INTERFACE_FILE_PATTERNS
from .steps import create_api_interface_step, create_owasp_mapping_step
from .types import (
    AgentInput,
    ApiInterfaceDiscoveryInput,
    ApiInterfaceResult,
    CombinedApiSecurityResult,
    OwaspMappingInput,
    OwaspMappingResult,
)
from .utils import (
    create_api_summary,
    create_security_summary,
    deduplicate_api_versioning,
    deduplicate_data_flows,
    deduplicate_data_models,
    deduplicate_graphql_fields,
    deduplicate_rest_endpoints,
    deduplicate_security_controls,
    deduplicate_vulnerabilities,
    deduplicate_websocket_connections,
)


@workflow("api_interface_discovery")
class ApiInterfaceDiscoveryWorkflow(ChunkProcessingMixin, Workflow[ApiInterfaceDiscoveryInput, Dict[str, Any]]):
    """
    Analyzes source code and API specifications to extract API interface information
    and map findings to OWASP API Security Top 10 2023 vulnerabilities.

    Step 1 - API Interface Discovery:
    - REST API endpoints and their specifications
    - GraphQL schemas, queries, and mutations
    - WebSocket connections and real-time communication
    - Data models and serialization formats
    - API versioning strategies and documentation
    - Data flow patterns and transformation logic

    Step 2 - OWASP API Security Mapping:
    - Maps API interface findings to OWASP API Security Top 10 2023 categories
    - Uses tree sitter tools to analyze code patterns for security vulnerabilities
    - Identifies missing security controls and potential attack vectors
    - Provides remediation advice and risk assessments
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Initialize LLM
        self.llm = LiteLLM.from_config(self.config)

        # Keep steps as lazy since they depend on project setup for tools
        self._api_interface_step: Optional[LLMStep[AgentInput, ApiInterfaceResult]] = None
        self._owasp_mapping_step: Optional[LLMStep[OwaspMappingInput, OwaspMappingResult]] = None

        # Store project path early when it's still valid
        self._project_path: Optional[str] = None

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for API interface discovery."""
        return API_INTERFACE_FILE_PATTERNS

    @property
    def api_interface_step(self) -> LLMStep[AgentInput, ApiInterfaceResult]:
        """Lazily initialize the API interface analysis step with tools."""
        if self._api_interface_step is None:
            self._api_interface_step = create_api_interface_step(self.llm, self.config, self._project_path)
        return self._api_interface_step

    @property
    def owasp_mapping_step(self) -> LLMStep[OwaspMappingInput, OwaspMappingResult]:
        """Lazily initialize the OWASP API Security mapping step with tools."""
        if self._owasp_mapping_step is None:
            self._owasp_mapping_step = create_owasp_mapping_step(self.llm, self.config, self._project_path)
        return self._owasp_mapping_step

    async def _process_single_chunk(
        self,
        chunk: CodeChunk,
        focus_api_types: Optional[List[str]] = None,
        include_data_models: bool = True,
        detect_versioning: bool = True,
    ) -> List[CombinedApiSecurityResult]:
        """Process a single chunk for API interface analysis and OWASP security mapping."""
        try:
            self.config.logger.debug(f"Processing API interface chunk: {Path(chunk.file_path)}")

            # Step 1: Run API interface analysis
            chunk_input = AgentInput(
                code=chunk,
                config=self.config,
            )

            api_result = await self.api_interface_step.run(chunk_input)

            # Step 2: Run OWASP mapping analysis using API interface results
            self.config.logger.debug(f"Running OWASP security mapping for chunk: {Path(chunk.file_path)}")

            owasp_input = OwaspMappingInput(
                code=chunk,
                api_interface_findings=api_result.model_dump_json(),
                config=self.config,
            )

            owasp_result = await self.owasp_mapping_step.run(owasp_input)

            # Combine results
            combined_result = CombinedApiSecurityResult(
                api_interface=api_result, security_analysis=owasp_result, file_path=chunk.file_path
            )

            return [combined_result]

        except Exception as e:
            self.config.logger.error(
                f"Failed to process API interface chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return []

    async def _aggregate_results(self, chunk_results: List[CombinedApiSecurityResult]) -> Dict[str, Any]:
        """Aggregate API interface results from multiple chunks."""

        if not chunk_results:
            self.config.logger.warning("No API interface chunks processed successfully")
            return {
                "rest_endpoints": [],
                "graphql_schema": [],
                "websocket_connections": [],
                "data_models": [],
                "api_versioning": [],
                "data_flows": [],
                "confidence_score": 0.0,
                "analysis_summary": "No API interface files found or processed",
                "files_analyzed": 0,
                "total_chunks_processed": 0,
                "vulnerabilities": [],
                "security_controls": [],
                "security_summary": {
                    "total_vulnerabilities": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                    "overall_security_posture": "unknown",
                    "confidence_score": 0.0,
                },
            }

        # Aggregate all API interface results
        all_rest_endpoints = []
        all_graphql_fields = []
        all_websocket_connections = []
        all_data_models = []
        all_api_versioning = []
        all_data_flows = []

        # Aggregate all security analysis results
        all_vulnerabilities = []
        all_security_controls = []

        for combined_result in chunk_results:
            # Extract API interface data
            api_result = combined_result.api_interface
            all_rest_endpoints.extend(api_result.rest_endpoints)
            all_graphql_fields.extend(api_result.graphql_schema)
            all_websocket_connections.extend(api_result.websocket_connections)
            all_data_models.extend(api_result.data_models)
            if api_result.api_versioning:
                all_api_versioning.extend(api_result.api_versioning)
            if api_result.data_flows:
                all_data_flows.extend(api_result.data_flows)

            # Extract security analysis data
            security_result = combined_result.security_analysis
            all_vulnerabilities.extend(security_result.vulnerabilities)
            all_security_controls.extend(security_result.security_controls_present)

        # Simple deduplication by key identifiers
        unique_rest_endpoints = deduplicate_rest_endpoints(all_rest_endpoints)
        unique_graphql_fields = deduplicate_graphql_fields(all_graphql_fields)
        unique_websocket_connections = deduplicate_websocket_connections(all_websocket_connections)
        unique_data_models = deduplicate_data_models(all_data_models)
        unique_api_versioning = deduplicate_api_versioning(all_api_versioning)
        unique_data_flows = deduplicate_data_flows(all_data_flows)

        # Deduplicate security analysis results
        unique_vulnerabilities = deduplicate_vulnerabilities(all_vulnerabilities)
        unique_security_controls = deduplicate_security_controls(all_security_controls)

        # Calculate confidence based on number of files and quality of findings
        total_findings = (
            len(unique_rest_endpoints)
            + len(unique_graphql_fields)
            + len(unique_websocket_connections)
            + len(unique_data_models)
        )
        confidence_score = min(0.9, 0.3 + (len(chunk_results) * 0.1) + (total_findings * 0.05))

        analysis_summary = create_api_summary(
            unique_rest_endpoints,
            unique_graphql_fields,
            unique_websocket_connections,
            unique_data_models,
            len(chunk_results),
        )

        # Calculate security summary
        security_summary = create_security_summary(unique_vulnerabilities)

        return {
            # API Interface Discovery Results
            "rest_endpoints": [endpoint.model_dump() for endpoint in unique_rest_endpoints],
            "graphql_schema": [field.model_dump() for field in unique_graphql_fields],
            "websocket_connections": [conn.model_dump() for conn in unique_websocket_connections],
            "data_models": [model.model_dump() for model in unique_data_models],
            "api_versioning": [version.model_dump() for version in unique_api_versioning],
            "data_flows": [flow.model_dump() for flow in unique_data_flows],
            "confidence_score": confidence_score,
            "analysis_summary": analysis_summary,
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results),
            # OWASP API Security Analysis Results
            "vulnerabilities": [vuln.model_dump() for vuln in unique_vulnerabilities],
            "security_controls": [control.model_dump() for control in unique_security_controls],
            "security_summary": security_summary,
        }

    def _print_owasp_security_summary(self, final_result: Dict[str, Any]) -> None:
        """Print a concise summary of OWASP security findings."""
        security_summary = final_result.get("security_summary", {})

        total_vulns = security_summary.get("total_vulnerabilities", 0)
        critical = security_summary.get("critical_count", 0)
        high = security_summary.get("high_count", 0)
        medium = security_summary.get("medium_count", 0)
        low = security_summary.get("low_count", 0)
        posture = security_summary.get("overall_security_posture", "unknown").upper()

        self.config.logger.info(
            f"OWASP Security Summary: {total_vulns} total vulnerabilities (Critical: {critical}, High: {high}, Medium: {medium}, Low: {low}) - Security Posture: {posture}"
        )

    async def workflow(self, input: ApiInterfaceDiscoveryInput) -> Dict[str, Any]:
        """Main API Interface Discovery and OWASP Security Mapping workflow."""
        try:
            self.config.logger.info("Starting API Interface Discovery and OWASP Security Mapping workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # Use project as context manager to keep temp directories alive
            with project:
                # Store project for lazy tool initialization
                self.project = project
                # Capture project path while it's still valid
                self._project_path = project.project_path

                # 2. Create a closure that captures workflow parameters
                async def chunk_processor(chunk: CodeChunk) -> List[CombinedApiSecurityResult]:
                    return await self._process_single_chunk(
                        chunk, input.focus_api_types, input.include_data_models, input.detect_versioning
                    )

                # 3. Process chunks concurrently using mixin utility
                chunk_results = await self.process_chunks_concurrently(
                    project=project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
                )

                # 4. Aggregate results
                final_result = await self._aggregate_results(chunk_results)

            self.config.logger.info(
                f"API Interface Discovery and OWASP Security Mapping completed. "
                f"Analyzed {final_result['files_analyzed']} files. "
                f"API Confidence: {final_result['confidence_score']:.2f}. "
                f"Found {final_result['security_summary']['total_vulnerabilities']} security issues."
            )

            # 5. Write output file if output_dir is configured
            write_json_output(results=final_result, workflow_name="api_interface_discovery", config=self.config)

            # 6. Print detailed OWASP security summary
            self._print_owasp_security_summary(final_result)

            return final_result

        except Exception as e:
            self.config.logger.error(f"Error during API interface discovery and OWASP security mapping: {str(e)}")
            raise e
