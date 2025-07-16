# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import argparse
import dataclasses
import logging
import multiprocessing as mp
import os
from pathlib import Path
from typing import Any, Dict, List, Type, Union, get_args, get_origin, get_type_hints

from fraim.config.config import Config
from fraim.observability import ObservabilityManager, ObservabilityRegistry
from fraim.observability.logging import make_logger
from fraim.scan import ScanArgs, scan
from fraim.validate_cli import validate_cli_args
from fraim.workflows import WorkflowRegistry


def parse_args_to_scan_args(args: argparse.Namespace) -> ScanArgs:
    """Convert argparse Namespace to typed ScanArgs dataclass."""

    # Extract workflow-specific arguments
    workflow_args = {}
    input_class = WorkflowRegistry.get_workflow_input_class(args.workflow)

    if input_class and dataclasses.is_dataclass(input_class):
        # Get all field names from the input dataclass
        field_names = {field.name for field in dataclasses.fields(input_class)}

        # Extract workflow-specific arguments from parsed args
        for field_name in field_names:
            if field_name not in {"config"}:  # Skip reserved fields
                arg_name = field_name
                if hasattr(args, arg_name):
                    workflow_args[field_name] = getattr(args, arg_name)

    return ScanArgs(
        workflow=args.workflow,
        workflow_args=workflow_args,
    )


def parse_args_to_config(args: argparse.Namespace) -> Config:
    """Convert FetchRepoArgs to Config object."""
    output_dir = args.output if args.output else str(Path(__file__).parent.parent / "fraim_output")

    # Default logger
    logger = make_logger(
        name="fraim",
        level=logging.DEBUG if args.debug else logging.INFO,
        path=os.path.join(output_dir, "fraim_scan.log"),
        show_logs=args.show_logs,
    )
    return Config(
        logger=logger,
        output_dir=output_dir,
        model=args.model,
        max_iterations=args.max_iterations,
        confidence=args.confidence,
        temperature=args.temperature,
    )


def setup_observability(args: argparse.Namespace, config: Config) -> ObservabilityManager:
    """Setup observability backends based on CLI arguments."""
    manager = ObservabilityManager(args.observability or [], logger=config.logger)
    manager.setup()
    return manager


def build_workflow_arg(parser: argparse.ArgumentParser) -> None:
    """Add workflow argument to the parser."""
    # Get available workflows from registry
    available_workflows = WorkflowRegistry.get_available_workflows()
    workflow_descriptions = WorkflowRegistry.get_workflow_descriptions()

    workflow_choices = sorted(available_workflows)

    # Build help text dynamically
    help_parts = []
    for workflow in workflow_choices:
        description = workflow_descriptions.get(workflow, "No description available")
        help_parts.append(f"{workflow}: {description}")
    workflow_help = f" - {'\n - '.join(help_parts)}"

    parser.add_argument("workflow", choices=workflow_choices, help=workflow_help)


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


def setup_workflow_subparsers(parser: argparse.ArgumentParser) -> None:
    """Setup subparsers for each workflow with auto-generated arguments."""
    # Get available workflows from registry
    available_workflows = WorkflowRegistry.get_available_workflows()
    workflow_descriptions = WorkflowRegistry.get_workflow_descriptions()
    all_cli_args = WorkflowRegistry.get_all_workflow_cli_args()

    # Create subparsers for workflows
    subparsers = parser.add_subparsers(
        dest="workflow",
        title="Available Workflows",
        description="Choose a workflow to run",
        help="Workflow-specific commands",
        required=True,
    )

    # Create a subparser for each workflow
    for workflow_name in available_workflows:
        workflow_parser = subparsers.add_parser(
            workflow_name,
            help=workflow_descriptions.get(workflow_name, "No description available"),
            description=workflow_descriptions.get(workflow_name, "No description available"),
        )

        # Add auto-generated workflow-specific arguments
        cli_args = all_cli_args.get(workflow_name, [])
        for arg_config in cli_args:
            # Make a copy to avoid mutating the original
            arg_config_copy = arg_config.copy()
            arg_name = arg_config_copy.pop("name")
            workflow_parser.add_argument(arg_name, **arg_config_copy)


def cli() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    #############################
    # Scan Args
    #############################
    setup_workflow_subparsers(parser)
    build_observability_arg(parser)

    #############################
    # Configuration
    #############################
    parser.add_argument("--output", help="Path to save the output HTML report")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--model",
        default="gemini/gemini-2.5-flash",
        help="Gemini model to use for initial scan (default: gemini/gemini-2.5-flash)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum number of tool calling iterations for vulnerability analysis (default: 50)",
    )
    parser.add_argument(
        "--confidence",
        type=int,
        choices=range(1, 11),
        default=7,
        help="Minimum confidence threshold (1-10) for filtering findings (default: 7)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0, help="Temperature setting for the model (0.0-1.0, default: 0)"
    )

    parser.add_argument("--show-logs", type=bool, default=True, help="Prints logs to standard error output")

    parsed_args = parser.parse_args()

    # Validate arguments
    try:
        validate_cli_args(parsed_args)
    except Exception as e:
        print(f"CLI Validation Error: {e}")
        exit(1)

    # Parse config to get logger
    config = parse_args_to_config(parsed_args)

    # Setup observability with config logger
    setup_observability(parsed_args, config)

    # Parse scan arguments
    args = parse_args_to_scan_args(parsed_args)

    # Run the scan with observability backends
    scan(args, config, observability_backends=parsed_args.observability)

    return 0


if __name__ == "__main__":
    # Set start method for multiprocessing
    mp.set_start_method("spawn", force=True)
    cli()
