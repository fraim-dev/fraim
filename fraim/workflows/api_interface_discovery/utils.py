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
    SecurityControl,
    Vulnerability,
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


def deduplicate_vulnerabilities(vulnerabilities: List[Vulnerability]) -> List[Vulnerability]:
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


def deduplicate_security_controls(controls: List[SecurityControl]) -> List[SecurityControl]:
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


def create_security_summary(vulnerabilities: List[Vulnerability]) -> Dict[str, Any]:
    """Create security analysis summary."""
    critical_count = sum(1 for v in vulnerabilities if v.risk_level.lower() == "critical")
    high_count = sum(1 for v in vulnerabilities if v.risk_level.lower() == "high")
    medium_count = sum(1 for v in vulnerabilities if v.risk_level.lower() == "medium")
    low_count = sum(1 for v in vulnerabilities if v.risk_level.lower() == "low")

    total_vulnerabilities = len(vulnerabilities)

    # Determine overall security posture
    if critical_count > 0 or high_count > 2:
        overall_posture = "weak"
    elif high_count > 0 or medium_count > 3:
        overall_posture = "moderate"
    else:
        overall_posture = "strong"

    # Calculate average confidence
    avg_confidence = sum(v.confidence for v in vulnerabilities) / len(vulnerabilities) if vulnerabilities else 0.0

    return {
        "total_vulnerabilities": total_vulnerabilities,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "overall_security_posture": overall_posture,
        "confidence_score": avg_confidence,
    }
