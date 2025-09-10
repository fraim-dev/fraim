import argparse
import os
from typing import TypedDict


class ProviderDetails(TypedDict):
    """Type definition for provider details."""

    env_var: str
    example_model: str
    display_name: str


def validate_cli_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Validate CLI arguments."""
    # Validate model and API key compatibility
    validate_model_api_key(parser, args)
    validate_git_diff(parser, args)


def validate_git_diff(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.head and not args.diff:
        parser.error("--head requires --diff")
    if args.base and not args.diff:
        parser.error("--base requires --diff")


def validate_model_api_key(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Validate that the model and API key match."""
    model = args.model
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

                parser.error(
                    f"The selected model is {model}, but you provided an API key for {other_provider_display} ({other_env_var}). "
                    f"Specify a {other_provider_display} model (Ex: --model={example_model}) or provide an API key for {provider_display} ({expected_env_var})."
                )
        # No API key provided at all
        parser.error(f"Please provide your API key for model {model} via the env var {expected_env_var}")
