# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Langfuse observability backend.
"""

import os

from ..base import ObservabilityBackend


class LangfuseBackend(ObservabilityBackend):
    """Langfuse observability backend implementation."""

    def get_name(self) -> str:
        """Return the backend name."""
        return "langfuse"

    def get_description(self) -> str:
        """Return a short description for CLI help."""
        return "LLM observability and analytics platform"

    def get_required_env_vars(self) -> list[str]:
        """Return list of required environment variables."""
        return ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]

    def get_optional_env_vars(self) -> dict[str, str]:
        """Return dict of optional env vars with their defaults."""
        return {"LANGFUSE_HOST": "http://localhost:3000"}

    def validate_config(self) -> bool:
        """Check if the backend is properly configured."""
        required_vars = self.get_required_env_vars()

        for var in required_vars:
            value = os.getenv(var)
            if not value or value.strip() == "":
                return False

        return True

    def setup_callbacks(self) -> list[str]:
        """Return the callback names for litellm."""
        return ["langfuse"]

    def setup_environment(self) -> None:
        """Setup environment variables for Langfuse."""
        # Set optional environment variables if not already set
        optional_vars = self.get_optional_env_vars()
        for var, default_value in optional_vars.items():
            if not os.getenv(var):
                os.environ[var] = default_value

    def get_config_help(self) -> str:
        """Return help text for configuring this backend."""
        return """  Langfuse Configuration:
  Required environment variables:
    LANGFUSE_PUBLIC_KEY - Your Langfuse public key (starts with pk-lf-...)
    LANGFUSE_SECRET_KEY - Your Langfuse secret key (starts with sk-lf-...)

  Optional environment variables:
    LANGFUSE_HOST - Langfuse host URL (default: http://localhost:3000)

  To get your API keys:
    1. Go to your Langfuse dashboard (http://localhost:3000 or https://cloud.langfuse.com)
    2. Create or select a project
    3. Navigate to Settings > API Keys
    4. Copy your Public Key and Secret Key

  Example setup:
    export LANGFUSE_PUBLIC_KEY="pk-lf-your-key-here"
    export LANGFUSE_SECRET_KEY="sk-lf-your-key-here"
    export LANGFUSE_HOST="http://localhost:3000"  # optional"""
