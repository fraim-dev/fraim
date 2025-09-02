# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Abstract base class for observability backends.
"""

from abc import ABC, abstractmethod


class ObservabilityBackend(ABC):
    """Abstract base class for LLM observability backends."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the backend name (e.g., 'langfuse')."""

    @abstractmethod
    def get_description(self) -> str:
        """Return a short description for CLI help."""

    @abstractmethod
    def get_required_env_vars(self) -> list[str]:
        """Return list of required environment variables."""

    @abstractmethod
    def get_optional_env_vars(self) -> dict[str, str]:
        """Return dict of optional env vars with their defaults."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Check if the backend is properly configured."""

    @abstractmethod
    def setup_callbacks(self) -> list[str]:
        """Return the callback names for litellm."""

    @abstractmethod
    def get_config_help(self) -> str:
        """Return help text for configuring this backend."""

    def setup_environment(self) -> None:
        """Setup environment variables if needed. Override if custom setup required."""
