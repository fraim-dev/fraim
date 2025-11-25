# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Observability setup utilities for CLI."""

from typing import Any

import typer

from fraim.observability import ObservabilityManager, ObservabilityRegistry


def setup_observability(backends: list[str]) -> ObservabilityManager:
    """Setup observability backends based on CLI arguments.

    Args:
        backends: List of observability backend names to enable

    Returns:
        Configured ObservabilityManager
    """
    manager = ObservabilityManager(backends)
    manager.setup()
    return manager


def get_observability_option() -> Any:
    """Get the Typer Option configuration for observability backends.

    Returns:
        Typer Option instance with help text for observability backends
    """
    # Get available observability backends
    available_backends = ObservabilityRegistry.get_available_backends()
    backend_descriptions = ObservabilityRegistry.get_backend_descriptions()

    # Build observability help text dynamically
    observability_help_parts = []
    for backend in sorted(available_backends):
        description = backend_descriptions.get(backend, "No description available")
        observability_help_parts.append(f"{backend}: {description}")

    help_text = f"Enable LLM observability backends.\n - {'\n - '.join(observability_help_parts)}"

    return typer.Option(default=None, help=help_text)
