# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import argparse
import asyncio
import dataclasses
import io
import logging
import multiprocessing as mp
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import is_dataclass
from types import UnionType
from typing import Annotated, Any, TextIO, Union, get_args, get_origin, get_type_hints

from rich.console import Console
from rich.live import Live

from fraim.core.workflows.discovery import discover_workflows
from fraim.observability import ObservabilityManager, ObservabilityRegistry
from fraim.observability.logging import setup_logging
from fraim.util import tty
from fraim.validate_cli import validate_cli_args

logger = logging.getLogger(__name__)


def setup_observability(args: argparse.Namespace) -> ObservabilityManager:
    """Setup observability backends based on CLI arguments."""
    manager = ObservabilityManager(args.observability or [])
    manager.setup()
    return manager


def build_observability_arg(parser: argparse.ArgumentParser) -> None:
    """Add observability argument to the parser."""
    # Get available observability backends
    available_backends = ObservabilityRegistry.get_available_backends()
    backend_descriptions = ObservabilityRegistry.get_backend_descriptions()

    # Build observability help text dynamically
    observability_help_parts = []
    for backend in sorted(available_backends):
        description = backend_descriptions.get(backend, "No description available")
        observability_help_parts.append(f"{backend}: {description}")

    observability_help = f"Enable LLM observability backends.\n - {'\n - '.join(observability_help_parts)}"

    parser.add_argument("--observability", nargs="+", choices=available_backends, default=[], help=observability_help)


def cli() -> int:
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--show-logs",
        action="store_true",
        help="Force printing of logs. Logs are automatically shown on stderr if rich\n"
        "display is not enabled or if stderr does not point to the same\n"
        "destination as stdout.",
    )
    parser.add_argument("--log-output", type=str, default="fraim_output", help="Output directory for logs")
    parser.add_argument(
        "--show-rich-display",
        action="store_true",
        help="Force display of the rich workflow progress, instead of showing logs. Rich\n"
        "display is automatically enabled if standard output is a TTY.",
    )

    build_observability_arg(parser)

    actions = parser.add_subparsers(dest="action")

    run_parser = actions.add_parser("run", help="Run a workflow")

    workflows_parser = run_parser.add_subparsers(dest="workflow", required=True)

    discovered_workflows = discover_workflows()  # TODO: support custom paths, maybe env var or initial args parse

    for workflow_name, workflow_class in discovered_workflows.items():
        workflow_parser = workflows_parser.add_parser(workflow_name, help=workflow_class.__doc__)

        """
        TODO: 
            Move the workflow-specific arg registration into a class method
            on the workflow. The default (on the `Workflow` base class) can
            to infer the args from the `Input` dataclass, as done here.  But if a
            workflow wants to handle args differently, it could override that method.
        
            Here the call should look something like:
                workflow_class = discovered_workflows[parsed_args.workflow]
                workflow_class.register_args(workflow_parser)
        """
        workflow_options = workflow_class.options()
        if workflow_options is None:
            continue

        workflow_args = workflow_options_to_cli_args(workflow_options)
        for arg_name, arg_kwargs in workflow_args.items():
            workflow_parser.add_argument(arg_name, **arg_kwargs)

    parsed_args = parser.parse_args()
    validate_cli_args(parser, parsed_args)

    # Determine whether to show rich display (on stdout) and logs (on stderr)
    show_rich_display = parsed_args.show_rich_display or tty.is_tty(sys.stdout)
    show_logs = (
        parsed_args.show_logs or not show_rich_display or not tty.streams_have_same_destination(sys.stdout, sys.stderr)
    )

    setup_logging(
        level=logging.DEBUG if parsed_args.debug else logging.INFO,
        path=os.path.join(parsed_args.log_output, "fraim_scan.log"),
        show_logs=show_logs,
    )

    setup_observability(parsed_args)

    for workflow_name, workflow_class in discovered_workflows.items():
        if workflow_name != parsed_args.workflow:
            continue

        workflow_kwargs = {}
        workflow_options = workflow_class.options()
        if workflow_options is None:
            continue

        if is_dataclass(workflow_options):
            for workflow_option in dataclasses.fields(workflow_options):
                if hasattr(parsed_args, workflow_option.name):
                    workflow_kwargs[workflow_option.name] = getattr(parsed_args, workflow_option.name)
        """
        TODO:
            Move the arg conversion and class instantiation into a class method on the
            workflow. The default implementation on the `Workflow` base class can do the
            namespace -> args conversion done here.  But workflows with special requirements
            can override that method entirely.
    
            The call here should look something like:
            
                workflow_class = discovered_workflows[parsed_args.workflow]
                workflow = workflow_class.from_args(parsed_args)
        """
        workflow = workflow_class(args=workflow_options(**workflow_kwargs))

        try:
            if show_rich_display:
                # Use rich display instead of logging

                async def run_with_rich_display() -> None:
                    with buffered_stdout() as original_stdout:
                        console = Console(file=original_stdout)
                        layout = workflow.rich_display()
                        with Live(
                            layout,
                            console=console,
                            screen=True,
                            redirect_stdout=False,
                            refresh_per_second=10,
                            auto_refresh=True,
                        ) as _live:
                            await workflow.run()

                asyncio.run(run_with_rich_display())
            else:
                # Use traditional logging
                logger.info(f"Running workflow: {workflow.name}")
                asyncio.run(workflow.run())
        except KeyboardInterrupt:
            logger.info("Workflow cancelled")
            return 1
        except Exception as e:
            logger.error(f"Workflow error: {e!s}")
            raise e

    return 0


def workflow_options_to_cli_args(options_class: type[Any]) -> dict[str, dict[str, Any]]:
    """Infer CLI arguments from a dataclass."""
    if not dataclasses.is_dataclass(options_class):
        return {}

    cli_args = {}
    type_hints = get_type_hints(options_class, include_extras=True)

    # Reserved fields that shouldn't become CLI arguments
    reserved_fields = {"config"}

    for field in dataclasses.fields(options_class):
        if field.name in reserved_fields:
            continue

        arg_name = f"--{field.name.replace('_', '-')}"
        field_type = type_hints.get(field.name, str)

        arg_config: dict[str, Any] = {
            "help": f"{field.name.replace('_', ' ').title()}",
        }

        # Extract metadata from Annotated types
        annotation_metadata = {}
        actual_type = field_type

        # Check if this is an Annotated type
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            if args:
                actual_type = args[0]  # The actual type is the first argument
                # The metadata is in the remaining arguments
                for metadata_item in args[1:]:
                    if isinstance(metadata_item, dict):
                        annotation_metadata.update(metadata_item)

        # Handle different field types (use actual_type instead of field_type)
        if actual_type == bool:
            if field.default is False:
                arg_config["action"] = "store_true"
            elif field.default is True:
                arg_config["action"] = "store_false"
        elif actual_type == int:
            arg_config["type"] = int
        elif actual_type == float:
            arg_config["type"] = float
        elif get_origin(actual_type) is list:
            arg_config["nargs"] = "+"
        elif get_origin(actual_type) is Union or get_origin(actual_type) is UnionType:
            # Handle Optional[T] which is Union[T, None]
            args = get_args(actual_type)
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                if non_none_type == int:
                    arg_config["type"] = int
                elif non_none_type == float:
                    arg_config["type"] = float
                elif get_origin(non_none_type) is list:
                    # Handle Optional[List[T]] - e.g., Optional[List[str]]
                    arg_config["nargs"] = "+"

        # Set default value
        if field.default is not dataclasses.MISSING:
            arg_config["default"] = field.default
            arg_config["required"] = False
        elif field.default_factory is not dataclasses.MISSING:
            arg_config["default"] = field.default_factory()
            arg_config["required"] = False

        # Apply metadata from annotations (this takes precedence)
        if annotation_metadata:
            if "choices" in annotation_metadata:
                arg_config["choices"] = annotation_metadata["choices"]
            if "help" in annotation_metadata:
                arg_config["help"] = annotation_metadata["help"]

        # Fallback to dataclass field metadata
        if hasattr(field, "metadata"):
            if "choices" in field.metadata and "choices" not in arg_config:
                arg_config["choices"] = field.metadata["choices"]
            if "help" in field.metadata and "help" not in arg_config:
                arg_config["help"] = field.metadata["help"]

        cli_args[arg_name] = arg_config

    return cli_args


@contextmanager
def buffered_stdout() -> Generator[TextIO | Any, None, None]:
    """
    Context manager that captures stdout during execution and replays it after exit.

    This is designed to work with Rich's Live display in screen mode. When Live uses
    screen=True, it switches to an alternate terminal screen, causing any stdout
    output (like print statements) during the Live display to be lost when returning
    to the main screen.

    This context manager:
    1. Redirects sys.stdout to a buffer during the 'with' block
    2. Yields the original stdout for use by Rich's Live display
    3. Replays all captured stdout content to the terminal after the 'with' block exits

    Usage:
        with buffered_stdout() as original_stdout:
            console = Console(file=original_stdout) # Use the real stdout for the Live display
            with Live(layout, console=console, screen=True) as live:
                print("This will be captured and shown after Live exits")
                # Live display code here
        # Captured print output appears here

    Returns:
        The original stdout stream for use by Rich's console
    """
    # String buffer to capture stdout while the live display is active
    buf = io.StringIO()

    old_out = sys.stdout
    try:
        sys.stdout = buf
        yield old_out
    finally:
        sys.stdout = old_out
        sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    # Set start method for multiprocessing
    mp.set_start_method("spawn", force=True)
    cli()
