# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Manager for LLM observability backends.
"""

import logging
from typing import Any

import litellm

from .registry import ObservabilityRegistry

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manager for setting up and configuring observability backends."""

    def __init__(self, enabled_backends: list[str]):
        """Initialize with list of backend names to enable and a logger."""
        self.enabled_backends = enabled_backends
        self.configured_backends: list[str] = []
        self.failed_backends: list[str] = []

    def setup(self) -> None:
        """Setup all enabled and properly configured backends."""
        if not self.enabled_backends:
            logger.info("No observability backends enabled. Use --observability to enable.")
            return

        success_callbacks: list[Any] = []
        failure_callbacks: list[Any] = []

        for backend_name in self.enabled_backends:
            backend = ObservabilityRegistry.get_backend(backend_name)
            if not backend:
                logger.warning(f"Unknown observability backend: {backend_name}")
                self.failed_backends.append(backend_name)
                continue

            try:
                if backend.validate_config():
                    # Setup environment if needed
                    backend.setup_environment()

                    # Get callbacks
                    callbacks = backend.setup_callbacks()
                    success_callbacks.extend(callbacks)
                    failure_callbacks.extend(callbacks)

                    self.configured_backends.append(backend_name)
                    logger.info(f"{backend.get_name()} observability enabled")
                else:
                    logger.warning(f"{backend.get_name()} not configured properly")
                    logger.info(f"Configuration help for {backend.get_name()}:\n{backend.get_config_help()}")
                    self.failed_backends.append(backend_name)
            except Exception as e:
                logger.error(f"Error setting up {backend_name}: {e}")
                self.failed_backends.append(backend_name)

        # Configure litellm callbacks if we have any working backends
        if success_callbacks:
            litellm.success_callback = success_callbacks
            litellm.failure_callback = failure_callbacks
            logger.info(f"LLM observability active with {len(self.configured_backends)} backend(s)")

    def get_status(self) -> dict[str, Any]:
        """Return status of all backends."""
        return {
            "enabled": self.enabled_backends,
            "configured": self.configured_backends,
            "failed": self.failed_backends,
            "total_requested": len(self.enabled_backends),
            "total_configured": len(self.configured_backends),
        }

    def is_enabled(self) -> bool:
        """Check if any observability backend is successfully configured."""
        return len(self.configured_backends) > 0
