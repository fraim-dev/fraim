from collections.abc import Callable
from typing import TypeVar, cast

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.text import Text

from fraim.outputs import sarif

T = TypeVar("T")


class ResultsPanel:
    """
    A Rich console panel that displays analysis results with counts.

    This panel shows the total number of results found. For SARIF results specifically,
    it provides specialized display with severity-based breakdowns (errors, warnings, notes).
    """

    def __init__(self, get_results: Callable[[], list[T]]) -> None:
        """
        Initialize the results panel with a function to retrieve results.

        Args:
            get_results: A callable that returns the list of results to display.
                        Results can be of any type T, with special handling for SARIF results.
        """
        self.get_results = get_results

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """
        Render the results panel for Rich console display.

        Args:
            console: The Rich console instance
            options: Console rendering options

        Yields:
            Panel: A Rich panel containing the formatted results information
        """

        results = self.get_results()

        text = Text()

        # Total results
        text.append("Results found: ", style="gray")
        text.append(f"{len(results)}", style="bold gray" if len(results) > 0 else "dim")

        # Check if we have SARIF results and show severity breakdown
        # TODO: This is a hacky way to specialize the display for SARIF. Figure out a better
        # way for a workflow to customize the results.
        if results and isinstance(results[0], sarif.Result):
            for breakdown_text, style in _render_severity_breakdown(cast("list[sarif.Result]", results)):
                text.append(breakdown_text, style=style)

        yield Panel(text, title="Results", border_style="green")


def _render_severity_breakdown(results: list[sarif.Result]) -> list[tuple[str, str]]:
    """
    Render severity breakdown for SARIF results.

    Args:
        results: List of SARIF Result objects

    Returns:
        List of (text, style) tuples for the breakdown parts
    """
    severity_counts = {"error": 0, "warning": 0, "note": 0}
    for result in results:
        if result.level in severity_counts:
            severity_counts[result.level] += 1

    breakdown_parts = []
    breakdown_parts.append((" ( ", "gray"))
    breakdown_parts.append(("", "gray"))
    breakdown_parts.append((f"Errors: {severity_counts['error']}", "bold red"))

    breakdown_parts.append((" | ", "gray"))
    breakdown_parts.append((f"Warnings: {severity_counts['warning']}", "bold orange1"))

    breakdown_parts.append((" | ", "gray"))
    breakdown_parts.append((f"Notes: {severity_counts['note']}", "bold blue"))

    breakdown_parts.append((" )", "gray"))

    return breakdown_parts
