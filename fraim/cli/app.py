# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Main Typer application for fraim CLI."""

import logging
import os
from dataclasses import dataclass, field
from typing import Annotated

import typer

from fraim import __version__
from fraim.cli.commands.run import app as run_app
from fraim.cli.commands.view import app as view_app
from fraim.cli.utils.display import should_show_logs, should_show_rich_display
from fraim.cli.utils.observability import setup_observability
from fraim.observability.logging import setup_logging

# Create the main Typer app
app = typer.Typer(
    help="A CLI app that runs AI-powered security workflows",
    no_args_is_help=True,
)


# Global state to pass between callbacks and commands
@dataclass
class GlobalState:
    """Global state container for CLI execution."""

    debug: bool = False
    show_logs: bool = False
    show_rich_display: bool = False
    log_output: str = "fraim_output"
    observability: list[str] = field(default_factory=list)


state = GlobalState()


def version_callback(value: bool) -> None:
    """Callback for --version flag."""
    if value:
        typer.echo(f"fraim {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version and exit"),
    ] = None,
    debug: Annotated[bool, typer.Option("--debug", help="Enable debug logging")] = False,
    show_logs: Annotated[
        bool,
        typer.Option(
            "--show-logs",
            help="Force printing of logs. Logs are automatically shown on stderr if rich\n"
            "display is not enabled or if stderr does not point to the same\n"
            "destination as stdout.",
        ),
    ] = False,
    log_output: Annotated[str, typer.Option("--log-output", help="Output directory for logs")] = "fraim_output",
    show_rich_display_flag: Annotated[
        bool,
        typer.Option(
            "--show-rich-display",
            help="Force display of the rich workflow progress, instead of showing logs. Rich\n"
            "display is automatically enabled if standard output is a TTY.",
        ),
    ] = False,
    observability: Annotated[
        list[str] | None, typer.Option(help="Enable LLM observability backends (e.g., langfuse)")
    ] = None,
) -> None:
    """Main CLI entry point with global options."""
    # Store global state
    state.debug = debug
    state.show_logs = show_logs
    state.show_rich_display = should_show_rich_display(show_rich_display_flag)
    state.log_output = log_output
    state.observability = observability if observability is not None else []

    # Setup observability
    setup_observability(state.observability)

    # Setup logging
    show_logs_final = should_show_logs(state.show_logs, state.show_rich_display)
    log_path = os.path.join(log_output, "fraim_scan.log")
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(level=log_level, path=log_path, show_logs=show_logs_final)


# Add command sub-apps
app.add_typer(view_app)
app.add_typer(run_app, name="run")


def cli() -> int:
    """Main CLI entry point.

    This function is called when the user runs the fraim command.
    """
    # Run the main app
    try:
        app()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception:
        return 1


if __name__ == "__main__":
    cli()
