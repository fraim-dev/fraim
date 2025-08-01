# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Discovery Workflow - Optimized 6-Agent Design

Maps system architecture through specialized analysis agents with maximum parallelization.
Each chunk is processed by all relevant agents simultaneously using asyncio.gather.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union, cast

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
from fraim.workflows.infrastructure_discovery.workflow import InfrastructureDiscoveryWorkflow
from fraim.workflows.api_interface_discovery.workflow import ApiInterfaceDiscoveryWorkflow

# Comprehensive file patterns for architecture discovery
FILE_PATTERNS = [
    # Infrastructure & Container files
    "Dockerfile", ".dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "*.k8s.yaml", "*.k8s.yml", "deployment.yaml", "service.yaml", "ingress.yaml",
    "*.tf", "*.tfvars", "*.hcl", "terraform.tfstate",

    # Configuration files
    "*.yaml", "*.yml", "*.json", "*.toml", "*.ini", "*.conf", "*.config",
    "*.properties", "*.env", ".env*", "*.settings",

    # Build & Package files
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
    "pom.xml", "build.gradle", "Cargo.toml", "composer.json", "Gemfile",
    "Makefile", "makefile", "*.mk",

    # API & Schema files
    "openapi.json", "swagger.json", "*.openapi.yaml", "*.swagger.yaml",
    "*.graphql", "*.proto",

    # Source code files
    "*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.java", "*.go", "*.rb",
    "*.php", "*.rs", "*.cs", "*.swift", "*.cpp", "*.c", "*.h",

    # Framework-specific files
    "settings.py", "urls.py", "views.py", "models.py",  # Django
    "app.py", "routes.py", "config.py",  # Flask
    "server.js", "app.js", "index.js", "main.js",  # Node.js
    "Application.java", "Controller.java", "Service.java",  # Spring
    "*.component.ts", "*.service.ts", "*.module.ts",  # Angular
]

# Load agent prompts (excluding infrastructure prompts since we use the infrastructure_discovery workflow)
SERVICE_DEPENDENCY_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "service_dependency_prompts.yaml")
)
EXTERNAL_INTEGRATION_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__),
                 "external_integration_prompts.yaml")
)
# API_INTERFACE_PROMPTS now handled by api_interface_discovery workflow
SECURITY_BOUNDARY_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "security_boundary_prompts.yaml")
)
SYNTHESIS_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "synthesis_prompts.yaml")
)


# Pydantic models for Agent 2: Service Dependencies (keeping the models that are specific to this workflow)
class DatabaseConnection(BaseModel):
    database_name: str
    database_type: str
    connection_details: Dict[str, Any]
    confidence: float


class ServiceDependencyResult(BaseModel):
    internal_services: List[Dict[str, Any]]
    database_connections: List[DatabaseConnection]
    message_queues: List[Dict[str, Any]]
    caching_layers: List[Dict[str, Any]]


# Pydantic models for Agent 3: External Integrations
class CloudService(BaseModel):
    provider: str
    service_name: str
    service_type: str
    confidence: float


class ExternalIntegrationResult(BaseModel):
    cloud_services: List[CloudService]
    third_party_apis: List[Dict[str, Any]]
    saas_integrations: List[Dict[str, Any]]


# API Interface models are now imported from api_interface_discovery workflow


# Pydantic models for Agent 5: Security Boundaries
class AuthenticationMechanism(BaseModel):
    auth_type: str
    implementation: str
    confidence: float


class SecurityBoundaryResult(BaseModel):
    authentication_mechanisms: List[AuthenticationMechanism]
    authorization_models: List[Dict[str, Any]]
    trust_boundaries: List[Dict[str, Any]]
    encryption_controls: List[Dict[str, Any]]


# Pydantic models for Agent 6: Architecture Synthesis
class ArchitectureOverview(BaseModel):
    system_type: str
    deployment_model: str
    architecture_pattern: str
    primary_technologies: List[str]
    description: str


class ArchitectureSynthesisResult(BaseModel):
    architecture_overview: ArchitectureOverview
    component_map: List[Dict[str, Any]]
    data_flow_diagram: Dict[str, Any]
    external_integrations: List[Dict[str, Any]]
    trust_boundaries: List[Dict[str, Any]]
    attack_surface: Dict[str, Any]
    security_assessment: Dict[str, Any]
    architecture_diagram_description: str


# Input classes for each agent
@dataclass
class AgentInput:
    file_path: str
    content: str
    config: Config


@dataclass
class SynthesisInput:
    infrastructure_results: str
    service_dependency_results: str
    external_integration_results: str
    api_interface_results: str
    security_boundary_results: str
    files_analyzed: int
    analysis_summary: str
    config: Config


@dataclass
class ArchitectureDiscoveryInput(ChunkWorkflowInput):
    """Input for the optimized Architecture Discovery workflow."""

    focus_areas: Annotated[
        List[str],
        {"help": "Focus areas: infrastructure, services, external, apis, security, all"}
    ] = field(default_factory=lambda: ["all"])

    enable_parallel_agents: Annotated[
        bool,
        {"help": "Run all relevant agents in parallel per chunk"}
    ] = True

    agent_retry_attempts: Annotated[
        int,
        {"help": "Number of retry attempts for rate-limited agents"}
    ] = 3

    agent_retry_delay: Annotated[
        int,
        {"help": "Base delay in seconds for agent retries"}
    ] = 2

    synthesis_timeout: Annotated[
        int,
        {"help": "Timeout in seconds for synthesis agent"}
    ] = 120


@workflow("architecture_discovery")
class ArchitectureDiscoveryWorkflow(ChunkProcessingMixin, Workflow[ArchitectureDiscoveryInput, Dict[str, Any]]):
    """
    Optimized 6-Agent Architecture Discovery Workflow

    Agents run in parallel per chunk for maximum efficiency:
    1. Infrastructure Analysis - containers, orchestration, deployment
    2. Service Dependencies - databases, queues, internal services
    3. External Integrations - cloud services, third-party APIs
    4. API Interfaces - REST, GraphQL, WebSocket endpoints
    5. Security Boundaries - auth, authorization, trust zones
    6. Architecture Synthesis - combines all findings
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self.llm = LiteLLM.from_config(self.config)

        # Initialize agents that don't need tree sitter tools immediately
        self._setup_basic_agents()

        self._service_dependency_agent: Optional[LLMStep[AgentInput,
                                                         ServiceDependencyResult]] = None
        self._external_integration_agent: Optional[LLMStep[AgentInput,
                                                           ExternalIntegrationResult]] = None
        self._security_boundary_agent: Optional[LLMStep[AgentInput,
                                                        SecurityBoundaryResult]] = None

    def _setup_basic_agents(self) -> None:
        """Initialize agents that don't require tree sitter tools."""

        self.infrastructure_discovery_workflow: InfrastructureDiscoveryWorkflow = InfrastructureDiscoveryWorkflow(
            self.config)

        self.api_interface_discovery_workflow: ApiInterfaceDiscoveryWorkflow = ApiInterfaceDiscoveryWorkflow(
            self.config)

        synthesis_parser = PydanticOutputParser(ArchitectureSynthesisResult)
        self.synthesis_agent: LLMStep[SynthesisInput, ArchitectureSynthesisResult] = LLMStep(
            self.llm, SYNTHESIS_PROMPTS["system"], SYNTHESIS_PROMPTS["user"], synthesis_parser
        )

    @property
    def service_dependency_agent(self) -> LLMStep[AgentInput, ServiceDependencyResult]:
        """Lazily initialize the service dependency agent with tree sitter tools."""
        if self._service_dependency_agent is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError(
                    "project_path must be set before accessing service_dependency_agent")

            tree_sitter_tools = TreeSitterTools(
                self.project.project_path).tools
            enhanced_llm = self.llm.with_tools(tree_sitter_tools)
            service_parser = PydanticOutputParser(ServiceDependencyResult)
            self._service_dependency_agent = LLMStep(
                enhanced_llm, SERVICE_DEPENDENCY_PROMPTS["system"], SERVICE_DEPENDENCY_PROMPTS["user"], service_parser
            )
        return self._service_dependency_agent

    @property
    def external_integration_agent(self) -> LLMStep[AgentInput, ExternalIntegrationResult]:
        """Lazily initialize the external integration agent with tree sitter tools."""
        if self._external_integration_agent is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError(
                    "project_path must be set before accessing external_integration_agent")

            tree_sitter_tools = TreeSitterTools(
                self.project.project_path).tools
            enhanced_llm = self.llm.with_tools(tree_sitter_tools)
            external_parser = PydanticOutputParser(ExternalIntegrationResult)
            self._external_integration_agent = LLMStep(
                enhanced_llm, EXTERNAL_INTEGRATION_PROMPTS[
                    "system"], EXTERNAL_INTEGRATION_PROMPTS["user"], external_parser
            )
        return self._external_integration_agent


    @property
    def security_boundary_agent(self) -> LLMStep[AgentInput, SecurityBoundaryResult]:
        """Lazily initialize the security boundary agent with tree sitter tools."""
        if self._security_boundary_agent is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError(
                    "project_path must be set before accessing security_boundary_agent")

            tree_sitter_tools = TreeSitterTools(
                self.project.project_path).tools
            enhanced_llm = self.llm.with_tools(tree_sitter_tools)
            security_parser = PydanticOutputParser(SecurityBoundaryResult)
            self._security_boundary_agent = LLMStep(
                enhanced_llm, SECURITY_BOUNDARY_PROMPTS["system"], SECURITY_BOUNDARY_PROMPTS["user"], security_parser
            )
        return self._security_boundary_agent

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for architecture discovery."""
        return FILE_PATTERNS

    def _determine_relevant_agents(self, file_path: str, focus_areas: List[str]) -> List[str]:
        """Intelligently determine which agents should analyze this file."""
        path = Path(file_path)
        file_name = path.name.lower()
        extension = path.suffix.lower()

        relevant_agents = []

        # Check if we should run all agents
        if "all" in focus_areas:
            return ["infrastructure", "services", "external", "apis", "security"]

        # Infrastructure files
        if any(term in file_name for term in ["docker", "k8s", "terraform", "deploy"]) or \
           extension in [".tf", ".tfvars"] or \
           "infrastructure" in focus_areas:
            relevant_agents.append("infrastructure")

        # Service dependency files
        if any(term in file_name for term in ["config", "settings", "database", "cache", "queue"]) or \
           extension in [".yaml", ".yml", ".json", ".conf"] or \
           "services" in focus_areas:
            relevant_agents.append("services")

        # External integration files
        if any(term in file_name for term in ["api", "integration", "external", "cloud"]) or \
           "external" in focus_areas:
            relevant_agents.append("external")

        # API interface files (source code)
        if extension in [".py", ".js", ".ts", ".java", ".go", ".rb", ".php"] or \
           any(term in file_name for term in ["api", "endpoint", "route", "controller"]) or \
           "apis" in focus_areas:
            relevant_agents.append("apis")

        # Security files
        if any(term in file_name for term in ["auth", "security", "permission", "policy"]) or \
           "security" in focus_areas:
            relevant_agents.append("security")

        # Default: if no specific matches, run basic analysis
        if not relevant_agents:
            relevant_agents = ["services", "external", "apis"]

        return relevant_agents

    async def _run_agent_safely(self, agent_name: str, agent_input: AgentInput, max_retries: int = 3, base_delay: int = 2) -> Optional[Dict[str, Any]]:
        """Run a single agent with error handling and rate limit retry logic."""

        for attempt in range(max_retries + 1):
            try:
                if agent_name == "infrastructure":
                    # Create a CodeChunk from the current file data
                    code_chunk = CodeChunk(
                        file_path=agent_input.file_path,
                        content=agent_input.content,
                        line_number_start_inclusive=1,
                        line_number_end_inclusive=len(
                            agent_input.content.splitlines())
                    )
                    # Call infrastructure discovery workflow's chunk processor
                    process_chunk_method = getattr(
                        self.infrastructure_discovery_workflow, '_process_single_chunk')
                    infrastructure_results = await process_chunk_method(code_chunk)
                    # Return the first result if available, converted to dict
                    if infrastructure_results:
                        return cast(Dict[str, Any], infrastructure_results[0].model_dump())
                    else:
                        return None
                elif agent_name == "services":
                    services_result = await self.service_dependency_agent.run(agent_input)
                    return services_result.model_dump()
                elif agent_name == "external":
                    external_result = await self.external_integration_agent.run(agent_input)
                    return external_result.model_dump()
                elif agent_name == "apis":
                    # Create a CodeChunk from the current file data for API interface discovery
                    code_chunk = CodeChunk(
                        file_path=agent_input.file_path,
                        content=agent_input.content,
                        line_number_start_inclusive=1,
                        line_number_end_inclusive=len(
                            agent_input.content.splitlines())
                    )
                    # Ensure the API interface discovery workflow has the project set
                    if not hasattr(self.api_interface_discovery_workflow, 'project') or not getattr(self.api_interface_discovery_workflow, 'project', None):
                        setattr(self.api_interface_discovery_workflow,
                                'project', self.project)

                    # Call API interface discovery workflow's chunk processor
                    process_chunk_method = getattr(
                        self.api_interface_discovery_workflow, '_process_single_chunk')
                    api_results = await process_chunk_method(code_chunk)
                    # Return the first result if available, converted to dict
                    if api_results:
                        return cast(Dict[str, Any], api_results[0].model_dump())
                    else:
                        return None
                elif agent_name == "security":
                    security_result = await self.security_boundary_agent.run(agent_input)
                    return security_result.model_dump()
                else:
                    return None

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limiting errors
                if "rate" in error_str and "limit" in error_str or "quota" in error_str or "429" in error_str:
                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        delay = base_delay * \
                            (2 ** attempt) + (time.time() % 1)  # Add jitter
                        self.config.logger.warning(
                            f"{agent_name} agent hit rate limit for {agent_input.file_path}. "
                            f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self.config.logger.error(
                            f"{agent_name} agent failed after {max_retries + 1} attempts due to rate limits for {agent_input.file_path}"
                        )
                        return None
                else:
                    # For non-rate-limit errors, fail immediately
                    self.config.logger.warning(
                        f"{agent_name} agent failed for {agent_input.file_path}: {str(e)}")
                    return None

        return None

    async def _process_single_chunk(
        self,
        chunk: CodeChunk,
        focus_areas: List[str],
        enable_parallel: bool,
        agent_retry_attempts: int = 3,
        agent_retry_delay: int = 2
    ) -> Dict[str, Any]:
        """Process a single chunk through all relevant agents in parallel."""
        file_path = chunk.file_path
        content = chunk.content

        # Determine which agents should analyze this file
        relevant_agents = self._determine_relevant_agents(
            file_path, focus_areas)

        agent_input = AgentInput(
            file_path=file_path, content=content, config=self.config)

        if enable_parallel and len(relevant_agents) > 1:
            # Run all relevant agents in parallel using asyncio.gather
            self.config.logger.debug(
                f"Running {len(relevant_agents)} agents in parallel for {file_path}")

            tasks = [self._run_agent_safely(
                agent_name, agent_input, agent_retry_attempts, agent_retry_delay) for agent_name in relevant_agents]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results
            chunk_result = {
                "file_path": file_path,
                "agents_run": relevant_agents,
                "parallel_execution": True
            }

            for agent_name, result in zip(relevant_agents, results):
                if isinstance(result, Exception):
                    self.config.logger.warning(
                        f"Agent {agent_name} failed for {file_path}: {str(result)}")
                    chunk_result[f"{agent_name}_result"] = None
                else:
                    chunk_result[f"{agent_name}_result"] = result

        else:
            # Run agents sequentially (for single agent or debugging)
            chunk_result = {
                "file_path": file_path,
                "agents_run": relevant_agents,
                "parallel_execution": False
            }

            for agent_name in relevant_agents:
                result = await self._run_agent_safely(agent_name, agent_input, agent_retry_attempts, agent_retry_delay)
                chunk_result[f"{agent_name}_result"] = result

        return chunk_result

    def _aggregate_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from all chunks by agent type."""
        aggregated: Dict[str, Any] = {
            "infrastructure_results": [],
            "service_dependency_results": [],
            "external_integration_results": [],
            "api_interface_results": [],
            "security_boundary_results": [],
            "metadata": {
                "files_analyzed": 0,
                "agents_executed": 0,
                "parallel_executions": 0,
                "file_list": []
            }
        }

        for chunk_result in chunk_results:
            # Safety check: ensure chunk_result is a dictionary
            if not isinstance(chunk_result, dict):
                self.config.logger.warning(
                    f"Skipping invalid chunk_result: {type(chunk_result)} - {str(chunk_result)[:100]}")
                continue

            if "error" in chunk_result:
                continue

            aggregated["metadata"]["files_analyzed"] += 1
            file_path = chunk_result.get("file_path", "unknown")
            aggregated["metadata"]["file_list"].append(file_path)

            if chunk_result.get("parallel_execution", False):
                aggregated["metadata"]["parallel_executions"] += 1

            # Aggregate results by agent type
            for agent_type in ["infrastructure", "services", "external", "apis", "security"]:
                result_key = f"{agent_type}_result"
                if result_key in chunk_result and chunk_result[result_key]:
                    result_data = chunk_result[result_key]

                    if agent_type == "services":
                        aggregated["service_dependency_results"].append(
                            result_data)
                    elif agent_type == "external":
                        aggregated["external_integration_results"].append(
                            result_data)
                    elif agent_type == "apis":
                        aggregated["api_interface_results"].append(result_data)
                    elif agent_type == "security":
                        aggregated["security_boundary_results"].append(
                            result_data)
                    else:
                        aggregated[f"{agent_type}_results"].append(result_data)

                    aggregated["metadata"]["agents_executed"] += 1

        return aggregated

    async def _synthesize_architecture(self, aggregated_results: Dict[str, Any], max_retries: int = 3, base_delay: int = 5, timeout_seconds: int = 120) -> ArchitectureSynthesisResult:
        """Run Agent 6: Architecture Synthesis to create comprehensive analysis."""

        for attempt in range(max_retries + 1):
            try:
                self.config.logger.info(
                    f"Running architecture synthesis agent (attempt {attempt + 1}/{max_retries + 1})")

                # Prepare JSON strings for synthesis with safe access
                infrastructure_json = json.dumps(
                    aggregated_results.get("infrastructure_results", []), indent=2)
                service_json = json.dumps(
                    aggregated_results.get("service_dependency_results", []), indent=2)
                external_json = json.dumps(
                    aggregated_results.get("external_integration_results", []), indent=2)
                api_json = json.dumps(
                    aggregated_results.get("api_interface_results", []), indent=2)
                security_json = json.dumps(
                    aggregated_results.get("security_boundary_results", []), indent=2)

                # Safe metadata access
                metadata = aggregated_results.get("metadata", {})
                analysis_summary = (
                    f"Analyzed {metadata.get('files_analyzed', 0)} files with "
                    f"{metadata.get('agents_executed', 0)} agent executions. "
                    f"Parallel processing used for {metadata.get('parallel_executions', 0)} files."
                )

                synthesis_input = SynthesisInput(
                    infrastructure_results=infrastructure_json,
                    service_dependency_results=service_json,
                    external_integration_results=external_json,
                    api_interface_results=api_json,
                    security_boundary_results=security_json,
                    files_analyzed=metadata.get("files_analyzed", 0),
                    analysis_summary=analysis_summary,
                    config=self.config
                )

                # Run with timeout
                return await asyncio.wait_for(
                    self.synthesis_agent.run(synthesis_input),
                    timeout=timeout_seconds
                )

            except asyncio.TimeoutError:
                self.config.logger.warning(
                    f"Architecture synthesis timed out after {timeout_seconds}s (attempt {attempt + 1}/{max_retries + 1})"
                )
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    self.config.logger.info(
                        f"Retrying synthesis in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    self.config.logger.error(
                        "Architecture synthesis failed after all retries due to timeouts")
                    break

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limiting errors
                if "rate" in error_str and "limit" in error_str or "quota" in error_str or "429" in error_str:
                    if attempt < max_retries:
                        delay = base_delay * \
                            (2 ** attempt) + (time.time() % 1)  # Add jitter
                        self.config.logger.warning(
                            f"Architecture synthesis hit rate limit. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        self.config.logger.error(
                            "Architecture synthesis failed after all retries due to rate limits")
                        break
                else:
                    # For other errors, log and break
                    self.config.logger.error(
                        f"Architecture synthesis failed: {str(e)}")
                    break

        # Return minimal synthesis result if all attempts failed
        self.config.logger.warning(
            "Returning minimal synthesis result due to failures")
        return ArchitectureSynthesisResult(
            architecture_overview=ArchitectureOverview(
                system_type="unknown",
                deployment_model="unknown",
                architecture_pattern="unknown",
                primary_technologies=[],
                description="Architecture synthesis failed"
            ),
            component_map=[],
            data_flow_diagram={
                "description": "Analysis failed", "flows": []},
            external_integrations=[],
            trust_boundaries=[],
            attack_surface={"entry_points": [], "data_stores": []},
            security_assessment={"overall_risk": "unknown",
                                 "key_concerns": [], "recommendations": []},
            architecture_diagram_description="Architecture synthesis failed due to processing error"
        )

    async def workflow(self, input: ArchitectureDiscoveryInput) -> Dict[str, Any]:
        """Main optimized Architecture Discovery workflow with 6-agent parallelization."""
        try:
            self.config.logger.info(
                "Starting optimized Architecture Discovery workflow with 6 specialized agents")

            # 1. Setup project input
            self.project = self.setup_project_input(input)

            # 2. Create chunk processor with parallelization
            async def chunk_processor(chunk: CodeChunk) -> List[Dict[str, Any]]:
                result = await self._process_single_chunk(
                    chunk,
                    input.focus_areas,
                    input.enable_parallel_agents,
                    input.agent_retry_attempts,
                    input.agent_retry_delay
                )
                return [result]

            # 3. Process all chunks concurrently
            chunk_results = await self.process_chunks_concurrently(
                project=self.project,
                chunk_processor=chunk_processor,
                max_concurrent_chunks=input.max_concurrent_chunks
            )

            # 4. Aggregate results by agent type
            aggregated_results = self._aggregate_results(chunk_results)

            # 5. Run architecture synthesis (Agent 6)
            try:
                synthesis_result = await self._synthesize_architecture(
                    aggregated_results,
                    input.agent_retry_attempts,
                    input.agent_retry_delay,
                    input.synthesis_timeout
                )
            except Exception as synthesis_error:
                self.config.logger.error(
                    f"Architecture synthesis failed: {str(synthesis_error)}")
                raise

            # Safe access to metadata for logging
            metadata = aggregated_results.get("metadata", {})
            self.config.logger.info(
                f"Architecture Discovery completed successfully! "
                f"Analyzed {metadata.get('files_analyzed', 0)} files, "
                f"executed {metadata.get('agents_executed', 0)} agents, "
                f"with {metadata.get('parallel_executions', 0)} parallel chunk executions. "
                f"System type: {synthesis_result.architecture_overview.system_type}"
            )

            # 6. Create final comprehensive output
            final_result = {
                "architecture_analysis": synthesis_result.model_dump(),
                "raw_agent_results": aggregated_results,
                "execution_metadata": {
                    "total_files_analyzed": metadata.get("files_analyzed", 0),
                    "total_agent_executions": metadata.get("agents_executed", 0),
                    "parallel_chunk_executions": metadata.get("parallel_executions", 0),
                    "focus_areas": input.focus_areas,
                    "parallel_agents_enabled": input.enable_parallel_agents,
                    "file_list": metadata.get("file_list", [])
                }
            }

            # 7. Write output file if configured
            write_json_output(
                results=final_result,
                workflow_name="architecture_discovery",
                config=self.config,
                custom_filename="architecture_discovery_analysis.json"
            )

            return final_result

        except Exception as e:
            self.config.logger.error(
                f"Error during optimized architecture discovery: {str(e)}")
            raise
