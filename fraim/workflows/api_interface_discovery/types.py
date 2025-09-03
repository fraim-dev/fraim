# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery Types

Pydantic models and dataclasses for API interface discovery workflow.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel

from fraim.config import Config
from fraim.core.contextuals.code import CodeChunk
from fraim.core.workflows import ChunkProcessingOptions
from fraim.core.workflows.llm_processing import LLMProcessorOptions


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


@dataclass
class ApiInterfaceDiscoveryInput(ChunkProcessingOptions, LLMProcessorOptions):
    """Input for the API Interface Discovery workflow."""

    focus_api_types: Annotated[
        Optional[List[str]], {"help": "Specific API types to focus on (e.g., rest, graphql, websocket, grpc)"}
    ] = None

    include_data_models: Annotated[bool, {"help": "Include analysis of data models and schemas"}] = True

    detect_versioning: Annotated[bool, {"help": "Analyze API versioning strategies"}] = True


@dataclass
class AgentInput:
    """Input for analyzing a single API interface chunk."""

    code: CodeChunk
    config: Config
