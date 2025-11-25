# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Run command for executing workflows with lazy discovery.

This implementation uses a custom Click Group that discovers workflows lazily
when list_commands() or get_command() is called. This ensures workflows are
discovered at the right time, even when --help is used.
"""

import asyncio
import logging
from typing import Annotated, Any

import click
import typer
from rich.console import Console
from rich.live import Live
from typer.core import TyperCommand, TyperGroup

from fraim.cli.adapters import TyperOptionsAdapter
from fraim.cli.utils.display import buffered_stdout
from fraim.core.display import HistoryView
from fraim.core.workflows.discovery import discover_workflows

logger = logging.getLogger(__name__)

# Adapter for converting workflow Options to CLI parameters
adapter = TyperOptionsAdapter()


class LazyWorkflowGroup(TyperGroup):
    """Custom Typer Group that discovers workflows lazily.

    This overrides list_commands() and get_command() to discover workflows
    on-demand, which allows --help to work correctly and supports custom
    workflow paths.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._workflows: dict[str, Any] | None = None
        self._workflow_path: str | None = None

    def _discover_workflows(self) -> dict[str, Any]:
        """Discover workflows if not already discovered."""
        if self._workflows is not None:
            return self._workflows

        # TODO: Use self._workflow_path when discover_workflows() supports it
        if self._workflow_path:
            logger.info(f"Discovering workflows from: {self._workflow_path}")
            logger.warning("--workflow-path not yet fully implemented, using default location")

        self._workflows = discover_workflows()
        logger.debug(f"Discovered {len(self._workflows)} workflows: {list(self._workflows.keys())}")
        return self._workflows

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List available workflow commands."""
        # Get workflow_path from context params if it was set
        if ctx.params and "workflow_path" in ctx.params:
            self._workflow_path = ctx.params["workflow_path"]

        workflows = self._discover_workflows()
        return sorted(workflows.keys())

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a specific workflow command by name."""
        # Get workflow_path from context params if it was set
        if ctx.params and "workflow_path" in ctx.params:
            self._workflow_path = ctx.params["workflow_path"]

        workflows = self._discover_workflows()

        if cmd_name not in workflows:
            return None

        workflow_class = workflows[cmd_name]
        return _create_workflow_command(cmd_name, workflow_class)


def _create_workflow_command(workflow_name: str, workflow_class: Any) -> TyperCommand:
    """Create a Typer Command for a workflow with Rich formatting.

    Args:
        workflow_name: Name of the workflow
        workflow_class: Workflow class with options() method

    Returns:
        TyperCommand configured with the workflow's options and Rich formatting
    """
    options_class = workflow_class.options()

    if options_class is None:
        # Workflow has no options
        def simple_command() -> None:
            """Execute workflow with no options."""
            workflow = workflow_class(args=None)
            asyncio.run(workflow.run())

        return TyperCommand(
            name=workflow_name,
            callback=simple_command,
            help=workflow_class.__doc__ or f"Run the {workflow_name} workflow",
        )

    # Workflow has options - convert to Click parameters
    click_params = adapter.options_to_click_params(options_class)

    # Create command function
    def make_workflow_command(wf_class: Any, opt_class: Any) -> Any:
        """Create command function with closure over workflow class."""

        def workflow_command(**kwargs: Any) -> None:
            """Execute the workflow."""
            from fraim.cli.app import state

            try:
                options = adapter.extract_options(opt_class, **kwargs)
            except ValueError as e:
                # Validation error from options dataclass __post_init__
                raise click.UsageError(f"Invalid options: {e}") from e

            workflow = wf_class(args=options)

            try:
                if state.show_rich_display:

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

                            history_view = HistoryView(workflow.history, title=workflow.name)
                            history_view.print_full_history(console)

                    asyncio.run(run_with_rich_display())
                else:
                    logger.info(f"Running workflow: {workflow.name}")
                    asyncio.run(workflow.run())
            except KeyboardInterrupt:
                logger.info("Workflow cancelled")
                raise typer.Exit(code=1)
            except Exception as e:
                logger.error(f"Workflow error: {e!s}")
                raise

        return workflow_command

    return TyperCommand(
        name=workflow_name,
        callback=make_workflow_command(workflow_class, options_class),
        params=click_params,
        help=workflow_class.__doc__ or f"Run the {workflow_name} workflow",
    )


# Create Typer app but convert it to use our custom Click Group
app = typer.Typer(
    cls=LazyWorkflowGroup,
    help="Run a workflow",
    no_args_is_help=True,
)


# Add the workflow_path option via callback
# This executes early and stores the value in the context
@app.callback()
def run_callback(
    workflow_path: Annotated[
        str | None, typer.Option(help="Path to custom workflows directory (not yet implemented)")
    ] = None,
) -> None:
    """Run command options."""
    # The workflow_path will be available in ctx.params when list_commands/get_command are called
