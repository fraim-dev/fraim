# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery Utilities

Helper functions for API interface discovery workflow.
"""

from typing import Any, Dict, List

from .types import (
    APIVersioning,
    DataFlow,
    DataModel,
    GraphQLField,
    RestEndpoint,
    WebSocketConnection,
)


def deduplicate_rest_endpoints(endpoints: List[RestEndpoint]) -> List[RestEndpoint]:
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


def deduplicate_graphql_fields(fields: List[GraphQLField]) -> List[GraphQLField]:
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


def deduplicate_websocket_connections(connections: List[WebSocketConnection]) -> List[WebSocketConnection]:
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


def deduplicate_data_models(models: List[DataModel]) -> List[DataModel]:
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


def deduplicate_api_versioning(versions: List[APIVersioning]) -> List[APIVersioning]:
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


def deduplicate_data_flows(flows: List[DataFlow]) -> List[DataFlow]:
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


def create_api_summary(
    rest_endpoints: List[RestEndpoint],
    graphql_fields: List[GraphQLField],
    websocket_connections: List[WebSocketConnection],
    data_models: List[DataModel],
    files_analyzed: int,
) -> str:
    """Create a human-readable summary of API interface analysis."""
    summary_parts = [f"Analyzed {files_analyzed} files for API interfaces."]

    if rest_endpoints:
        summary_parts.append(f"Found {len(rest_endpoints)} REST endpoints")

    if graphql_fields:
        summary_parts.append(f"Found {len(graphql_fields)} GraphQL fields")

    if websocket_connections:
        summary_parts.append(f"Found {len(websocket_connections)} WebSocket connections")

    if data_models:
        summary_parts.append(f"Found {len(data_models)} data models")

    return " ".join(summary_parts)
