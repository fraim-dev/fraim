# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Configuration management for Gemini Scan.
"""

import logging
import os
from typing import Optional


class Config:
    """Configuration class for Gemini Scan."""

    def __init__(
        self,
        logger: logging.Logger,
        mcp_port: int = 8765,
        model: str = "gemini/gemini-2.5-flash",
        output_dir: str = "",
        temperature: float = 0,
        max_iterations: int = 50,
        host: str = "localhost",
        prompt: Optional[str] = None,
        confidence: int = 7,
        project_path: str = "",
    ):
        """
        Initialize configuration.

        Args:
            logger: The logger instance to use under this config
            model: Name of the model to use (e.g., "gemini/gemini-2.5-flash", "openai/gpt-4")
            output_dir: Directory to store scan outputs
            logger: Logger instance
            max_iterations: Maximum number of tool calling iterations
            project_path: Path to the project being scanned (set during scan)
            temperature: Temperature for model generation
            confidence: Minimum confidence threshold (1-10) for filtering findings
        """
        self.model = model

        # Validate that the correct API key environment variable is set
        api_key = self._get_api_key_for_model(model)
        if not api_key:
            provider = self._get_provider_from_model(model)
            env_var = self._get_env_var_for_provider(provider)
            raise ValueError(f"API key must be provided via {env_var} environment variable for {provider} models")
            # TODO: error log and exit non-zero

        # Set up scan directory
        os.makedirs(output_dir, exist_ok=True)

        self.output_dir = output_dir
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.confidence = confidence
        self.project_path = project_path
        self.logger = logger

    def _get_provider_from_model(self, model: str) -> str:
        """Extract the provider from the model name."""
        if "/" in model:
            return model.split("/")[0]
        return "unknown"

    def _get_env_var_for_provider(self, provider: str) -> str:
        """Get the expected environment variable name for a provider."""
        provider_env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "cohere": "COHERE_API_KEY",
            "azure": "AZURE_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
        }
        return provider_env_map.get(provider.lower(), f"{provider.upper()}_API_KEY")

    def _get_api_key_for_model(self, model_name: str) -> Optional[str]:
        """Get the API key for a given model from environment variables."""
        provider = self._get_provider_from_model(model_name)
        env_var = self._get_env_var_for_provider(provider)
        return os.environ.get(env_var)
