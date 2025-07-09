# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import argparse
import logging
import multiprocessing as mp
import os
from pathlib import Path

from fraim.observability.logging import make_logger
from fraim.scan import scan, ScanArgs
from fraim.config.config import Config
from fraim.observability import ObservabilityManager, ObservabilityRegistry
from fraim.scan import ScanArgs, scan
from fraim.workflows import WorkflowRegistry
from fraim.validate_cli import validate_cli_args


def parse_args_to_scan_args(args: argparse.Namespace) -> ScanArgs:
    """Convert argparse Namespace to typed FetchRepoArgs dataclass."""
    return ScanArgs(
        repo=args.repo,
        path=args.path,
        workflows=args.workflows,
        globs=args.globs,
        limit=args.limit
    )
    
def parse_args_to_config(args: argparse.Namespace) -> Config:
    """Convert FetchRepoArgs to Config object."""
    output_dir = args.output if args.output else str(Path(__file__).parent.parent / "fraim_output")

    # Default logger
    logger = make_logger(
        name="fraim",
        level = logging.DEBUG if args.debug else logging.INFO,
        path = os.path.join(output_dir, "fraim_scan.log"),
        show_logs=args.show_logs,
    )
    return Config(
        logger=logger,
        output_dir=output_dir,
        model=args.model,
        processes=args.processes,
        chunk_size=args.chunk_size,
        max_iterations=args.max_iterations,
        confidence=args.confidence,
        temperature=args.temperature,
    )


def setup_observability(args: argparse.Namespace, config: Config) -> ObservabilityManager:
    """Setup observability backends based on CLI arguments."""
    manager = ObservabilityManager(args.observability or [], logger=config.logger)
    manager.setup()
    return manager


def build_workflows_arg(parser: argparse.ArgumentParser) -> None:
    """Add workflows argument to the parser."""
    # Get available workflows from registry
    available_workflows = WorkflowRegistry.get_available_workflows()
    workflow_descriptions = WorkflowRegistry.get_workflow_descriptions()

    workflow_choices = sorted(available_workflows)

    # Build help text dynamically
    help_parts = []
    for workflow in workflow_choices:
        description = workflow_descriptions.get(workflow, "No description available")
        help_parts.append(f"{workflow}: {description}")
    workflows_help = f" - {'\n - '.join(help_parts)}"

    parser.add_argument("--workflows", nargs="+",
                        choices=workflow_choices, help=workflows_help, required=True)


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
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Scan a repository for security vulnerabilities.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    #############################
    # Scan Args
    #############################
    parser.add_argument("--repo", help="Repository URL to scan")
    parser.add_argument("--path", help="Local path to scan")
    parser.add_argument(
        "--globs",
        nargs="+",
        default=None,
        help="Globs to use for file scanning. If not provided, will use default globs.",
    )
    build_workflows_arg(parser)
    build_observability_arg(parser)

    #############################
    # Configuration
    #############################
    parser.add_argument("--output", help="Path to save the output HTML report")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--model",
        default="gemini/gemini-2.5-flash",
        help="Gemini model to use for initial scan (default: gemini-2.0-flash)",
    )
    parser.add_argument("--processes", type=int, default=8, help="Number of processes to use")
    parser.add_argument("--chunk-size", type=int, default=500, help="Number of lines per chunk")
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
    parser.add_argument("--limit", type=int, help="Limit the number of files to scan")

    parser.add_argument('--show-logs', type=bool, default=True, help='Prints logs to standard error output')

    parsed_args = parser.parse_args()

    if parsed_args.limit is not None and parsed_args.limit <= 0:
        parser.error("--limit must be a positive integer")

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
