# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery Workflow

Analyzes source code and API specifications to identify API endpoints, protocols, 
and interface contracts including REST, GraphQL, WebSocket endpoints, and data models.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.tools.tree_sitter import TreeSitterTools
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_json_output

# API-focused file patterns
API_INTERFACE_FILE_PATTERNS = [
    # API & Schema files
    "openapi.json", "swagger.json", "*.openapi.yaml", "*.swagger.yaml",
    "*.graphql", "*.proto", "*.avsc", "*.avdl",

    # Source code files (most likely to contain API definitions)
    "*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.java", "*.go", "*.rb",
    "*.php", "*.rs", "*.cs", "*.swift", "*.cpp", "*.c", "*.h",

    # Framework-specific files
    "settings.py", "urls.py", "views.py", "models.py",  # Django
    "app.py", "routes.py", "config.py", "*.blueprint.py",  # Flask
    "server.js", "app.js", "index.js", "main.js", "*.routes.js",  # Node.js
    "Application.java", "Controller.java", "Service.java", "*Controller.java",  # Spring
    "*.component.ts", "*.service.ts", "*.module.ts", "*.resolver.ts",  # Angular/NestJS

    # API documentation and configuration
    "*.yaml", "*.yml", "*.json", "*.toml",
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
    "pom.xml", "build.gradle", "Cargo.toml", "composer.json", "Gemfile",
]

# Load API interface prompts
API_INTERFACE_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "api_interface_prompts.yaml")
)

# Load OWASP API Security mapping prompts
OWASP_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "owasp_security_prompts.yaml")
)


# Pydantic models for API Interface Analysis
class RestEndpoint(BaseModel):
    endpoint_path: str
    http_method: str
    handler_function: Optional[str] = None
    middleware: Optional[List[str]] = None
    input_validation: Optional[Dict[str, Any]] = None
    response_format: Optional[Dict[str, Any]] = None
    rate_limiting: Optional[str] = None
    caching_strategy: Optional[str] = None
    confidence: float


class GraphQLField(BaseModel):
    schema_type: str  # query|mutation|subscription
    field_name: str
    arguments: Optional[List[Dict[str, Any]]] = None
    return_type: str
    resolver_function: Optional[str] = None
    complexity_score: Optional[int] = None
    deprecation_status: Optional[str] = None
    confidence: float


class WebSocketConnection(BaseModel):
    endpoint_path: str
    connection_handler: str
    message_types: Optional[List[str]] = None
    authentication_required: bool
    rate_limiting: Optional[str] = None
    connection_lifecycle: Optional[List[str]] = None
    broadcasting: Optional[str] = None
    confidence: float


class DataModel(BaseModel):
    model_name: str
    model_type: str  # entity|dto|request|response|event|other
    fields: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[str]] = None
    serialization_format: Optional[str] = None
    confidence: float


class APIVersioning(BaseModel):
    versioning_strategy: str  # url_path|header|query_param|content_type
    current_version: str
    supported_versions: Optional[List[str]] = None
    deprecation_timeline: Optional[str] = None
    breaking_changes: Optional[List[str]] = None
    migration_guide: Optional[str] = None
    confidence: float


class DataFlow(BaseModel):
    flow_name: str
    source: str
    destination: str
    data_format: str  # json|xml|binary|stream|other
    transformation_logic: Optional[str] = None
    error_handling: Optional[str] = None
    retry_strategy: Optional[str] = None
    monitoring: Optional[str] = None
    confidence: float


class ApiInterfaceResult(BaseModel):
    rest_endpoints: List[RestEndpoint]
    graphql_schema: List[GraphQLField]
    websocket_connections: List[WebSocketConnection]
    data_models: List[DataModel]
    api_versioning: Optional[List[APIVersioning]] = None
    data_flows: Optional[List[DataFlow]] = None


# Pydantic models for OWASP API Security Analysis
class CodeEvidence(BaseModel):
    file_path: str
    line_number: int
    code_snippet: str
    pattern_type: str


class TreeSitterFinding(BaseModel):
    query_used: str
    matches_found: int
    pattern_description: str


class Vulnerability(BaseModel):
    owasp_category: str  # API1:2023 through API10:2023
    vulnerability_title: str
    description: str
    affected_endpoints: List[str]
    code_evidence: List[CodeEvidence]
    tree_sitter_findings: List[TreeSitterFinding]
    risk_level: str  # critical|high|medium|low
    confidence: float
    remediation_advice: str


class SecurityControl(BaseModel):
    # authentication|authorization|rate_limiting|input_validation|encryption|logging
    control_type: str
    implementation: str
    endpoints_covered: List[str]
    effectiveness: str  # strong|moderate|weak


class SecuritySummary(BaseModel):
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_security_posture: str  # strong|moderate|weak
    confidence_score: float


class OwaspMappingResult(BaseModel):
    vulnerabilities: List[Vulnerability]
    security_controls_present: List[SecurityControl]
    summary: SecuritySummary


class CombinedApiSecurityResult(BaseModel):
    """Combined result containing both API interface findings and OWASP security analysis."""
    api_interface: ApiInterfaceResult
    security_analysis: OwaspMappingResult
    file_path: str


@dataclass
class ApiInterfaceDiscoveryInput(ChunkWorkflowInput):
    """Input for the API Interface Discovery workflow."""

    focus_api_types: Annotated[
        Optional[List[str]],
        {"help": "Specific API types to focus on (e.g., rest, graphql, websocket, grpc)"}
    ] = None

    include_data_models: Annotated[
        bool,
        {"help": "Include analysis of data models and schemas"}
    ] = True

    detect_versioning: Annotated[
        bool,
        {"help": "Analyze API versioning strategies"}
    ] = True


@dataclass
class AgentInput:
    """Input for analyzing a single API interface chunk."""

    file_path: str
    content: str
    config: Config


@dataclass
class OwaspMappingInput:
    """Input for analyzing API interface findings for OWASP vulnerabilities."""

    file_path: str
    content: str
    api_interface_findings: str  # JSON string of ApiInterfaceResult
    config: Config


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

        # API interface analysis step will be lazily initialized with tree sitter tools
        self._api_interface_step: Optional[LLMStep[AgentInput,
                                                   ApiInterfaceResult]] = None

        # OWASP mapping step will be lazily initialized with tree sitter tools
        self._owasp_mapping_step: Optional[LLMStep[OwaspMappingInput,
                                                   OwaspMappingResult]] = None

    @property
    def api_interface_step(self) -> LLMStep[AgentInput, ApiInterfaceResult]:
        """Lazily initialize the API interface analysis step with tree sitter tools."""
        if self._api_interface_step is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError(
                    "project_path must be set before accessing api_interface_step")

            tree_sitter_tools = TreeSitterTools(
                self.project.project_path).tools
            enhanced_llm = self.llm.with_tools(tree_sitter_tools)
            api_parser = PydanticOutputParser(ApiInterfaceResult)
            self._api_interface_step = LLMStep(
                enhanced_llm, API_INTERFACE_PROMPTS["system"], API_INTERFACE_PROMPTS["user"], api_parser
            )
        return self._api_interface_step

    @property
    def owasp_mapping_step(self) -> LLMStep[OwaspMappingInput, OwaspMappingResult]:
        """Lazily initialize the OWASP API Security mapping step with tree sitter tools."""
        if self._owasp_mapping_step is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError(
                    "project_path must be set before accessing owasp_mapping_step")

            tree_sitter_tools = TreeSitterTools(
                self.project.project_path).tools
            enhanced_llm = self.llm.with_tools(tree_sitter_tools)
            owasp_parser = PydanticOutputParser(OwaspMappingResult)
            self._owasp_mapping_step = LLMStep(
                enhanced_llm, OWASP_PROMPTS["system"], OWASP_PROMPTS["user"], owasp_parser
            )
        return self._owasp_mapping_step

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for API interface discovery."""
        return API_INTERFACE_FILE_PATTERNS

    async def _process_single_chunk(
        self,
        chunk: CodeChunk,
        focus_api_types: Optional[List[str]] = None,
        include_data_models: bool = True,
        detect_versioning: bool = True
    ) -> List[CombinedApiSecurityResult]:
        """Process a single chunk for API interface analysis and OWASP security mapping."""
        try:
            self.config.logger.debug(
                f"Processing API interface chunk: {Path(chunk.file_path)}")

            # Step 1: Run API interface analysis
            chunk_input = AgentInput(
                file_path=chunk.file_path,
                content=chunk.content,
                config=self.config,
            )

            api_result = await self.api_interface_step.run(chunk_input)

            # Step 2: Run OWASP mapping analysis using API interface results
            self.config.logger.debug(
                f"Running OWASP security mapping for chunk: {Path(chunk.file_path)}")

            owasp_input = OwaspMappingInput(
                file_path=chunk.file_path,
                content=chunk.content,
                api_interface_findings=api_result.model_dump_json(),
                config=self.config,
            )

            owasp_result = await self.owasp_mapping_step.run(owasp_input)

            # Combine results
            combined_result = CombinedApiSecurityResult(
                api_interface=api_result,
                security_analysis=owasp_result,
                file_path=chunk.file_path
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
            self.config.logger.warning(
                "No API interface chunks processed successfully")
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
            all_security_controls.extend(
                security_result.security_controls_present)

        # Simple deduplication by key identifiers
        unique_rest_endpoints = self._deduplicate_rest_endpoints(
            all_rest_endpoints)
        unique_graphql_fields = self._deduplicate_graphql_fields(
            all_graphql_fields)
        unique_websocket_connections = self._deduplicate_websocket_connections(
            all_websocket_connections)
        unique_data_models = self._deduplicate_data_models(all_data_models)
        unique_api_versioning = self._deduplicate_api_versioning(
            all_api_versioning)
        unique_data_flows = self._deduplicate_data_flows(all_data_flows)

        # Deduplicate security analysis results
        unique_vulnerabilities = self._deduplicate_vulnerabilities(
            all_vulnerabilities)
        unique_security_controls = self._deduplicate_security_controls(
            all_security_controls)

        # Calculate confidence based on number of files and quality of findings
        total_findings = len(unique_rest_endpoints) + len(unique_graphql_fields) + \
            len(unique_websocket_connections) + len(unique_data_models)
        confidence_score = min(
            0.9, 0.3 + (len(chunk_results) * 0.1) + (total_findings * 0.05))

        analysis_summary = self._create_api_summary(
            unique_rest_endpoints, unique_graphql_fields, unique_websocket_connections,
            unique_data_models, len(chunk_results)
        )

        # Calculate security summary
        security_summary = self._create_security_summary(
            unique_vulnerabilities)

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

    def _deduplicate_rest_endpoints(self, endpoints: List[RestEndpoint]) -> List[RestEndpoint]:
        """Remove duplicate REST endpoints."""
        seen = set()
        unique = []
        for endpoint in endpoints:
            # Use path and method as deduplication key
            key = f"{endpoint.endpoint_path}:{endpoint.http_method}"
            if key not in seen:
                seen.add(key)
                unique.append(endpoint)
        return unique

    def _deduplicate_graphql_fields(self, fields: List[GraphQLField]) -> List[GraphQLField]:
        """Remove duplicate GraphQL fields."""
        seen = set()
        unique = []
        for field in fields:
            # Use schema type and field name as deduplication key
            key = f"{field.schema_type}:{field.field_name}"
            if key not in seen:
                seen.add(key)
                unique.append(field)
        return unique

    def _deduplicate_websocket_connections(self, connections: List[WebSocketConnection]) -> List[WebSocketConnection]:
        """Remove duplicate WebSocket connections."""
        seen = set()
        unique = []
        for conn in connections:
            # Use endpoint path as deduplication key
            key = conn.endpoint_path
            if key not in seen:
                seen.add(key)
                unique.append(conn)
        return unique

    def _deduplicate_data_models(self, models: List[DataModel]) -> List[DataModel]:
        """Remove duplicate data models."""
        seen = set()
        unique = []
        for model in models:
            # Use model name and type as deduplication key
            key = f"{model.model_name}:{model.model_type}"
            if key not in seen:
                seen.add(key)
                unique.append(model)
        return unique

    def _deduplicate_api_versioning(self, versions: List[APIVersioning]) -> List[APIVersioning]:
        """Remove duplicate API versioning strategies."""
        seen = set()
        unique = []
        for version in versions:
            # Use versioning strategy as deduplication key
            key = version.versioning_strategy
            if key not in seen:
                seen.add(key)
                unique.append(version)
        return unique

    def _deduplicate_data_flows(self, flows: List[DataFlow]) -> List[DataFlow]:
        """Remove duplicate data flows."""
        seen = set()
        unique = []
        for flow in flows:
            # Use flow name and source-destination as deduplication key
            key = f"{flow.flow_name}:{flow.source}:{flow.destination}"
            if key not in seen:
                seen.add(key)
                unique.append(flow)
        return unique

    def _create_api_summary(self, rest_endpoints: List[RestEndpoint], graphql_fields: List[GraphQLField],
                            websocket_connections: List[WebSocketConnection], data_models: List[DataModel],
                            files_analyzed: int) -> str:
        """Create a human-readable summary of API interface analysis."""
        summary_parts = [
            f"Analyzed {files_analyzed} files for API interfaces."]

        if rest_endpoints:
            summary_parts.append(f"Found {len(rest_endpoints)} REST endpoints")

        if graphql_fields:
            summary_parts.append(f"Found {len(graphql_fields)} GraphQL fields")

        if websocket_connections:
            summary_parts.append(
                f"Found {len(websocket_connections)} WebSocket connections")

        if data_models:
            summary_parts.append(f"Found {len(data_models)} data models")

        return " ".join(summary_parts)

    def _deduplicate_vulnerabilities(self, vulnerabilities: List[Vulnerability]) -> List[Vulnerability]:
        """Remove duplicate vulnerabilities."""
        seen = set()
        unique = []
        for vuln in vulnerabilities:
            # Use OWASP category and title as deduplication key
            key = f"{vuln.owasp_category}:{vuln.vulnerability_title}"
            if key not in seen:
                seen.add(key)
                unique.append(vuln)
        return unique

    def _deduplicate_security_controls(self, controls: List[SecurityControl]) -> List[SecurityControl]:
        """Remove duplicate security controls."""
        seen = set()
        unique = []
        for control in controls:
            # Use control type and implementation as deduplication key
            key = f"{control.control_type}:{control.implementation}"
            if key not in seen:
                seen.add(key)
                unique.append(control)
        return unique

    def _create_security_summary(self, vulnerabilities: List[Vulnerability]) -> Dict[str, Any]:
        """Create security analysis summary."""
        critical_count = sum(
            1 for v in vulnerabilities if v.risk_level == "critical")
        high_count = sum(1 for v in vulnerabilities if v.risk_level == "high")
        medium_count = sum(
            1 for v in vulnerabilities if v.risk_level == "medium")
        low_count = sum(1 for v in vulnerabilities if v.risk_level == "low")

        total_vulnerabilities = len(vulnerabilities)

        # Determine overall security posture
        if critical_count > 0 or high_count > 2:
            overall_posture = "weak"
        elif high_count > 0 or medium_count > 3:
            overall_posture = "moderate"
        else:
            overall_posture = "strong"

        # Calculate average confidence
        avg_confidence = sum(v.confidence for v in vulnerabilities) / \
            len(vulnerabilities) if vulnerabilities else 0.0

        return {
            "total_vulnerabilities": total_vulnerabilities,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "overall_security_posture": overall_posture,
            "confidence_score": avg_confidence
        }

    def _print_owasp_security_summary(self, final_result: Dict[str, Any]) -> None:
        """Print a concise summary of OWASP security findings."""
        security_summary = final_result.get('security_summary', {})

        total_vulns = security_summary.get('total_vulnerabilities', 0)
        critical = security_summary.get('critical_count', 0)
        high = security_summary.get('high_count', 0)
        medium = security_summary.get('medium_count', 0)
        low = security_summary.get('low_count', 0)
        posture = security_summary.get(
            'overall_security_posture', 'unknown').upper()

        self.config.logger.info(
            f"OWASP Security Summary: {total_vulns} total vulnerabilities (Critical: {critical}, High: {high}, Medium: {medium}, Low: {low}) - Security Posture: {posture}")

    async def workflow(self, input: ApiInterfaceDiscoveryInput) -> Dict[str, Any]:
        """Main API Interface Discovery and OWASP Security Mapping workflow."""
        try:
            self.config.logger.info(
                "Starting API Interface Discovery and OWASP Security Mapping workflow")

            # 1. Setup project input using mixin utility
            self.project = self.setup_project_input(input)

            # 2. Create a closure that captures workflow parameters
            async def chunk_processor(chunk: CodeChunk) -> List[CombinedApiSecurityResult]:
                return await self._process_single_chunk(
                    chunk, input.focus_api_types, input.include_data_models, input.detect_versioning
                )

            # 3. Process chunks concurrently using mixin utility
            chunk_results = await self.process_chunks_concurrently(
                project=self.project,
                chunk_processor=chunk_processor,
                max_concurrent_chunks=input.max_concurrent_chunks
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
            write_json_output(
                results=final_result,
                workflow_name="api_interface_discovery",
                config=self.config
            )

            # 6. Print detailed OWASP security summary
            self._print_owasp_security_summary(final_result)

            return final_result

        except Exception as e:
            self.config.logger.error(
                f"Error during API interface discovery and OWASP security mapping: {str(e)}")
            raise e
