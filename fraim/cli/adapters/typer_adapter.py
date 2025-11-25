# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Typer adapter for converting workflow Options to Typer parameters."""

import dataclasses
from types import UnionType
from typing import Annotated, Any, Union, cast, get_args, get_origin, get_type_hints

import click
import typer

from fraim.cli.adapters.base import OptionsAdapter


class TyperOptionsAdapter(OptionsAdapter):
    """Adapter that converts dataclass Options to Typer parameters."""

    def options_to_parameters(self, options_class: type) -> dict[str, Any]:
        """Convert a dataclass Options to Typer parameter type annotations.

        Args:
            options_class: The Options dataclass to convert

        Returns:
            A dictionary mapping parameter names to Annotated types with typer.Option
        """
        if not dataclasses.is_dataclass(options_class):
            return {}

        params = {}
        type_hints = get_type_hints(options_class, include_extras=True)

        # Reserved fields that shouldn't become CLI arguments
        reserved_fields = {"config"}

        for field in dataclasses.fields(options_class):
            if field.name in reserved_fields:
                continue

            field_type = type_hints.get(field.name, str)

            # Extract help text from Annotated metadata or field metadata
            help_text = self._extract_help(field, field_type)

            # Extract the actual type (unwrap Annotated if present)
            actual_type = self._extract_actual_type(field_type)

            # Extract choices from metadata if present
            choices = self._extract_choices(field, field_type)

            # Build the typer.Option
            option_kwargs: dict[str, Any] = {"help": help_text}
            if choices:
                option_kwargs["case_sensitive"] = False

            # Determine default value
            if field.default is not dataclasses.MISSING:
                default = field.default
            elif field.default_factory is not dataclasses.MISSING:
                default = field.default_factory()
            else:
                default = ...  # Required

            # Handle different field types
            if actual_type == bool:
                # For booleans, use flags
                if default is False:
                    option_kwargs["is_flag"] = True
                    option_kwargs.pop("help", None)  # Help goes in Annotated
                    params[field.name] = Annotated[bool, typer.Option(default, **option_kwargs, help=help_text)]
                else:
                    params[field.name] = Annotated[bool, typer.Option(default, **option_kwargs, help=help_text)]
            elif get_origin(actual_type) is list:
                # Handle List types
                if default == dataclasses.MISSING or default == ...:
                    params[field.name] = Annotated[list[Any], typer.Option(**option_kwargs)]
                else:
                    params[field.name] = Annotated[list[Any], typer.Option(default, **option_kwargs)]
            elif get_origin(actual_type) in (Union, UnionType):
                # Handle Optional[T] which is Union[T, None]
                args = get_args(actual_type)
                if len(args) == 2 and type(None) in args:
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    if get_origin(non_none_type) is list:
                        # Handle Optional[List[T]]
                        params[field.name] = Annotated[list[Any] | None, typer.Option(default, **option_kwargs)]
                    else:
                        params[field.name] = Annotated[non_none_type | None, typer.Option(default, **option_kwargs)]
                else:
                    params[field.name] = Annotated[actual_type, typer.Option(default, **option_kwargs)]
            else:
                # Default handling for str, int, float, Path, etc.
                params[field.name] = Annotated[actual_type, typer.Option(default, **option_kwargs)]

        return params

    def extract_options(self, options_class: type, **kwargs: Any) -> Any:
        """Extract and instantiate the options dataclass from keyword arguments.

        Args:
            options_class: The Options dataclass to instantiate
            **kwargs: Parsed command-line arguments

        Returns:
            An instance of the options_class
        """
        # Filter kwargs to only include fields that exist in the dataclass
        valid_fields = {f.name for f in dataclasses.fields(options_class)}
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
        return options_class(**filtered_kwargs)

    def _extract_help(self, field: dataclasses.Field, field_type: type) -> str:
        """Extract help text from field metadata or Annotated type."""
        # First check Annotated metadata
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            for metadata_item in args[1:]:
                if isinstance(metadata_item, dict) and "help" in metadata_item:
                    return cast("str", metadata_item["help"])

        # Then check field metadata
        if hasattr(field, "metadata") and "help" in field.metadata:
            return cast("str", field.metadata["help"])

        # Fallback to field name
        return field.name.replace("_", " ").title()

    def _extract_actual_type(self, field_type: type) -> type:
        """Extract the actual type from Annotated wrapper."""
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            return args[0] if args else str
        return field_type

    def _extract_choices(self, field: dataclasses.Field, field_type: type) -> list[Any] | None:
        """Extract choices from field metadata or Annotated type."""
        # First check Annotated metadata
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            for metadata_item in args[1:]:
                if isinstance(metadata_item, dict) and "choices" in metadata_item:
                    return cast("list[Any]", metadata_item["choices"])

        # Then check field metadata
        if hasattr(field, "metadata") and "choices" in field.metadata:
            return cast("list[Any]", field.metadata["choices"])

        return None

    def options_to_click_params(self, options_class: type) -> list[Any]:
        """Convert a dataclass Options to Click Parameter objects.

        Args:
            options_class: The Options dataclass to convert

        Returns:
            A list of click.Option objects
        """
        if not dataclasses.is_dataclass(options_class):
            return []

        params = []
        type_hints = get_type_hints(options_class, include_extras=True)

        # Reserved fields that shouldn't become CLI arguments
        reserved_fields = {"config"}

        for field in dataclasses.fields(options_class):
            if field.name in reserved_fields:
                continue

            field_type = type_hints.get(field.name, str)

            # Extract help text
            help_text = self._extract_help(field, field_type)

            # Extract the actual type
            actual_type = self._extract_actual_type(field_type)

            # Determine default value
            if field.default is not dataclasses.MISSING:
                default = field.default
                required = False
            elif field.default_factory is not dataclasses.MISSING:
                default = field.default_factory()
                required = False
            else:
                default = None
                required = True

            # Convert field name to CLI option name
            param_name = f"--{field.name.replace('_', '-')}"

            # Build Click Option based on type
            if actual_type == bool:
                # Boolean flags
                if default is False:
                    params.append(
                        click.Option(
                            [param_name],
                            is_flag=True,
                            default=default,
                            help=help_text,
                        )
                    )
                else:
                    params.append(
                        click.Option(
                            [param_name],
                            is_flag=True,
                            flag_value=not default,
                            default=default,
                            help=help_text,
                        )
                    )
            elif actual_type == int:
                params.append(
                    click.Option(
                        [param_name],
                        type=click.INT,
                        default=default,
                        required=required,
                        help=help_text,
                    )
                )
            elif actual_type == float:
                params.append(
                    click.Option(
                        [param_name],
                        type=click.FLOAT,
                        default=default,
                        required=required,
                        help=help_text,
                    )
                )
            elif get_origin(actual_type) is list:
                # Handle List types
                params.append(
                    click.Option(
                        [param_name],
                        multiple=True,
                        default=default if default else None,
                        required=required and not default,
                        help=help_text,
                    )
                )
            elif get_origin(actual_type) in (Union, UnionType):
                # Handle Optional types
                args = get_args(actual_type)
                if len(args) == 2 and type(None) in args:
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    if non_none_type == int:
                        params.append(
                            click.Option(
                                [param_name],
                                type=click.INT,
                                default=default,
                                required=False,
                                help=help_text,
                            )
                        )
                    elif non_none_type == float:
                        params.append(
                            click.Option(
                                [param_name],
                                type=click.FLOAT,
                                default=default,
                                required=False,
                                help=help_text,
                            )
                        )
                    elif get_origin(non_none_type) is list:
                        params.append(
                            click.Option(
                                [param_name],
                                multiple=True,
                                default=default,
                                required=False,
                                help=help_text,
                            )
                        )
                    else:
                        params.append(
                            click.Option(
                                [param_name],
                                type=click.STRING,
                                default=default,
                                required=False,
                                help=help_text,
                            )
                        )
                else:
                    params.append(
                        click.Option(
                            [param_name],
                            type=click.STRING,
                            default=default,
                            required=required,
                            help=help_text,
                        )
                    )
            else:
                # Default to string
                params.append(
                    click.Option(
                        [param_name],
                        type=click.STRING,
                        default=default,
                        required=required,
                        help=help_text,
                    )
                )

        return params
