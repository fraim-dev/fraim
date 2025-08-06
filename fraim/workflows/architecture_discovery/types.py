# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Architecture Discovery Types

Data classes and type definitions for the Architecture Discovery workflow.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Optional

from fraim.core.workflows import ChunkWorkflowInput


@dataclass
class ArchitectureDiscoveryInput(ChunkWorkflowInput):
    """Input for the Architecture Discovery orchestrator workflow."""

    # Architecture-specific configuration options
    include_data_flows: Annotated[
        bool, {"help": "Generate detailed data flow analysis"}
    ] = True

    include_trust_boundaries: Annotated[
        bool, {"help": "Identify and map trust boundaries"}
    ] = True

    diagram_format: Annotated[
        str, {
            "help": "Output format for architecture diagrams (mermaid, plantuml, text)"}
    ] = "mermaid"

    # Rate limiting configuration
    api_delay_seconds: Annotated[
        float, {"help": "Delay between API calls to respect rate limits"}
    ] = 0.5

    reduce_concurrency_on_rate_limit: Annotated[
        bool, {"help": "Automatically reduce concurrency when rate limits are hit"}
    ] = True


@dataclass
class ComponentDiscoveryResults:
    """Container for component discovery results."""

    # Infrastructure Discovery Results
    infrastructure: Optional[Dict[str, Any]] = None

    # API Interface Discovery Results
    api_interfaces: Optional[Dict[str, Any]] = None

    # Synthesis results
    architecture_diagram: Optional[str] = None
    data_flows: Optional[List[Dict[str, Any]]] = None
    external_integrations: Optional[List[Dict[str, Any]]] = None
    trust_boundaries: Optional[List[Dict[str, Any]]] = None


@dataclass
class DataFlow:
    """Represents a data flow between components."""

    source: str
    target: str
    type: str
    category: str
    protocol: str
    port: Optional[int] = None
    direction: str = "bidirectional"
    data_classification: str = "unknown"
    encryption: bool = False
    authentication: str = "unknown"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExternalIntegration:
    """Represents an external system integration."""

    name: str
    type: str
    category: str
    protocol: str
    endpoint: Optional[str] = None
    authentication: str = "unknown"
    data_classification: str = "unknown"
    criticality: str = "medium"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TrustBoundary:
    """Represents a trust boundary in the system."""

    name: str
    type: str
    category: str
    components: List[str]
    security_controls: List[str]
    threat_level: str = "medium"
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
