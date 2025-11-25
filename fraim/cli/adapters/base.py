# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base adapter interface for converting workflow Options to CLI arguments."""

from abc import ABC, abstractmethod
from typing import Any


class OptionsAdapter(ABC):
    """Abstract interface for converting workflow Options to CLI arguments.

    This allows workflows to remain library-agnostic while supporting different
    CLI libraries (argparse, click, typer, etc.).
    """

    @abstractmethod
    def options_to_parameters(self, options_class: type) -> dict[str, Any]:
        """Convert a dataclass Options to CLI parameter specifications.

        Args:
            options_class: The Options dataclass to convert

        Returns:
            A dictionary mapping parameter names to their specifications
            (format depends on the CLI library)
        """

    @abstractmethod
    def extract_options(self, options_class: type, **kwargs: Any) -> Any:
        """Extract and instantiate the options dataclass from parsed CLI arguments.

        Args:
            options_class: The Options dataclass to instantiate
            **kwargs: Parsed command-line arguments

        Returns:
            An instance of the options_class
        """

    @abstractmethod
    def options_to_click_params(self, options_class: type) -> list[Any]:
        """Convert a dataclass Options to Click Parameter objects.

        This is used for dynamic command registration with Click's imperative API.

        Args:
            options_class: The Options dataclass to convert

        Returns:
            A list of click.Option or click.Argument objects
        """
