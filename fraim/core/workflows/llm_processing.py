# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
import os
from dataclasses import dataclass
from typing import Annotated, TypedDict

from fraim.core.llms import LiteLLM

logger = logging.getLogger(__name__)


@dataclass
class LLMOptions:
    """Base input for chunk-based workflows."""

    model: Annotated[str, {"help": "Model to use for initial scan (default: anthropic/claude-sonnet-4-0)"}] = (
        "anthropic/claude-sonnet-4-0"
    )

    temperature: Annotated[float, {"help": "Temperature setting for the model (0.0-1.0, default: 0)"}] = 0

    def __post_init__(self) -> None:
        """Validate LLM options after initialization."""
        if hasattr(super(), "__post_init__"):
            super().__post_init__()  # type: ignore

        validate_model_api_key(self.model)


class LLMMixin:
    def __init__(self, args: LLMOptions):
        super().__init__(args)  # type: ignore

        # Workaround for GPT-5 models, which don't support temperature
        if "gpt-5" in args.model:
            logger.warning("GPT-5 models don't support temperature, setting temperature to 1")
            args.temperature = 1
        if "gemini-3" in args.model and args.temperature < 1:
            logger.warning("Gemini 3 is unreliable with temperature less than 1, setting temperature to 1")
            args.temperature = 1

        self.llm = LiteLLM(
            model=args.model,
            additional_model_params={"temperature": args.temperature},
        )


class ProviderDetails(TypedDict):
    """Details about an LLM provider."""

    env_var: str
    example_model: str
    display_name: str


def validate_model_api_key(model: str) -> None:
    """Validate that the model and API key match.

    Args:
        model: The model name to validate

    Raises:
        ValueError: If API key is missing or mismatched with model provider
    """
    # Map providers to their expected environment variables
    provider_details: dict[str, ProviderDetails] = {
        "openai": {
            "env_var": "OPENAI_API_KEY",
            "example_model": "openai/gpt-4",
            "display_name": "OpenAI",
        },
        "anthropic": {
            "env_var": "ANTHROPIC_API_KEY",
            "example_model": "anthropic/claude-sonnet-4-0",
            "display_name": "Anthropic",
        },
        "gemini": {
            "env_var": "GEMINI_API_KEY",
            "example_model": "gemini/gemini-2.5-flash",
            "display_name": "Google",
        },
    }

    # Extract provider from model name
    if "/" not in model:
        # If no provider specified, skip validation
        return

    provider = model.split("/")[0].lower()

    # Check if we know about this provider
    if provider not in provider_details:
        # Unknown provider, skip validation
        return

    expected_env_var = provider_details[provider]["env_var"]

    # Check if the required API key is set
    if not os.environ.get(expected_env_var):
        # Check if user has other provider API keys set
        for _, details in provider_details.items():
            other_env_var = details["env_var"]
            if other_env_var and other_env_var != expected_env_var and os.environ.get(other_env_var):
                other_provider_display = details["display_name"]
                provider_display = provider_details[provider]["display_name"]

                example_model = details["example_model"]
                other_env_var = details["env_var"]

                raise ValueError(
                    f"The selected model is {model}, but you provided an API key for {other_provider_display} ({other_env_var}). "
                    f"Specify a {other_provider_display} model (Ex: --model={example_model}) or provide an API key for {provider_display} ({expected_env_var})."
                )
        # No API key provided at all
        raise ValueError(f"Please provide your API key for model {model} via the env var {expected_env_var}")
