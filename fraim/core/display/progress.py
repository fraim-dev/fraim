from collections.abc import Callable

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


class ProgressPanel:
    """
    A Rich-compatible panel that displays dynamic progress information.

    This class creates a styled progress panel with a progress bar, completion
    statistics, and elapsed time. The progress information is dynamically updated
    by calling a provided function that returns the current state.

    The panel includes:
    - Task description
    - Completion count and percentage
    - Visual progress bar
    - Elapsed time

    Example:
        >>> def get_current_progress():
        ...     return "Processing files", 75, 100
        >>> panel = ProgressPanel(get_current_progress)
        >>> console.print(panel)  # Displays progress panel
    """

    def __init__(self, get_progress: Callable[[], tuple[str, int, int]]) -> None:
        """
        Initialize the ProgressPanel with a progress information callback.

        Args:
            get_progress: A callable that returns current progress information
                         as a tuple of (description, completed, total).
                         - description (str): Text describing the current task
                         - completed (int): Number of completed items
                         - total (int): Total number of items to process

        The get_progress function will be called each time the panel is rendered
        to get the most up-to-date progress information.
        """
        self.get_progress = get_progress

        description, completed, total = self.get_progress()

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[green]{task.description}"),
            TextColumn("{task.completed}/{task.total} ({task.percentage:>0.0f}%) complete"),
            BarColumn(bar_width=None),
            TimeElapsedColumn(),
            expand=True,
        )

        self.task = self.progress.add_task(description, total=total, completed=completed)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """
        Render the progress panel for Rich console output.

        This method implements the Rich protocol for rendering. It updates the
        progress information by calling the get_progress callback and yields
        a Panel containing the formatted progress bar.

        Args:
            console: The Rich console instance
            options: Console rendering options

        Yields:
            Panel: A styled panel containing the progress bar with current information
        """
        description, completed, total = self.get_progress()

        self.progress.update(self.task, completed=completed, total=total, description=description)

        yield Panel(self.progress, title="Progress", border_style="cyan")
