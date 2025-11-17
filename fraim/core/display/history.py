# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Rich-based view for History."""

from rich.console import Console, ConsoleOptions, RenderResult
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from fraim.core.history import EventRecord, History, HistoryRecord


class HistoryView:
    """
    A Rich view of the history

    Shows the items in the history  , limiting to the number that will fit in the console.
    Nested items are indented.
    """

    def __init__(self, history: History, title: str = "History") -> None:
        self.history = history
        self.title = title

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Create a Rich panel displaying the history in a tree structure."""

        if not self.history.records:
            yield Panel(Text("No history available", style="dim"), title=self.title, border_style="blue")
            return

        # Calculate available height for the tree using options.height
        console_height = options.height or console.size.height

        # Reserve space for panel borders (2 lines) and cost display (1 line)
        max_lines = console_height - 3

        # Calculate available width for truncation
        # Account for panel padding (4 chars), timestamp (10 chars), and some buffer
        console_width = options.max_width or console.size.width
        available_width = console_width - 25  # Conservative buffer for padding and formatting

        panel = self._build_history_panel(max_lines=max_lines, available_width=available_width)
        yield panel

    def _build_history_tree(self, max_lines: int | None = None, available_width: int = 200) -> Tree:
        """
        Build a history tree with the execution records.

        Args:
            max_lines: Maximum number of records to display. If None, shows all records.
            available_width: Available width for description text before truncation.

        Returns:
            A Rich Tree containing the history
        """
        # Flatten all records
        all_records = self._flatten_records(self.history.records)

        # If max_lines specified, truncate to show most recent records
        if max_lines is not None and len(all_records) > max_lines:
            # Take the most recent records that fit
            records_to_display = all_records[-max_lines:]
        else:
            records_to_display = all_records

        # Get total cost for display (using sync version since Rich rendering is synchronous)
        total_cost = self.history.get_total_cost_sync()
        cost_text = f"[dim] | Total Cost: ${total_cost:0.2f}[/dim]" if total_cost > 0 else ""

        tree = Tree(f"{self.title}{cost_text}", style="bold blue")

        # Add the records to tree
        self._add_flattened_records_to_tree(records_to_display, tree, available_width)

        return tree

    def _build_history_panel(self, max_lines: int | None = None, available_width: int = 200) -> Panel:
        """
        Build a history panel with the execution tree.

        Args:
            max_lines: Maximum number of records to display. If None, shows all records.
            available_width: Available width for description text before truncation.

        Returns:
            A Rich Panel containing the history tree
        """
        tree = self._build_history_tree(max_lines=max_lines, available_width=available_width)
        return Panel(tree, title="Execution History", border_style="blue", padding=(1, 2))

    def _flatten_records(self, records: list, depth: int = 0) -> list[tuple]:
        """
        Flatten nested records into a chronological list with depth information.

        Returns a list of tuples: (record, depth, timestamp)
        """
        flattened = []

        for record in records:
            # Add the record itself
            flattened.append((record, depth, record.timestamp))

            # If it's a HistoryRecord with nested records, add those too
            if hasattr(record, "history") and record.history.records:
                nested = self._flatten_records(record.history.records, depth + 1)
                flattened.extend(nested)

        return flattened

    def _truncate_description(self, description: str, max_length: int, depth: int = 0) -> str:
        """
        Truncate description to a single line, replacing newlines with spaces.

        Args:
            description: The description text to truncate
            max_length: Maximum length before truncation based on available width
            depth: Tree depth level for calculating indentation space

        Returns:
            Truncated description string
        """
        # Replace newlines and multiple spaces with single spaces
        single_line = " ".join(description.split())

        # Account for tree indentation (approximately 2-4 chars per depth level)
        effective_width = max_length - (depth * 4)
        effective_width = max(effective_width, 30)  # Minimum reasonable width

        # Truncate if too long
        if len(single_line) > effective_width:
            return single_line[: effective_width - 3] + "..."

        return single_line

    def _add_flattened_records_to_tree(self, flattened_records: list[tuple], tree: Tree, available_width: int) -> None:
        """
        Add flattened records to the tree, reconstructing the hierarchy.

        Args:
            flattened_records: List of (record, depth, timestamp) tuples
            tree: The root tree node to add to
            available_width: Available width for truncating descriptions
        """
        # Keep track of nodes at each depth level to maintain hierarchy
        depth_nodes = {0: tree}

        for record, depth, _ in flattened_records:
            # Format timestamp for display
            timestamp_str = record.timestamp.strftime("%H:%M:%S")

            if isinstance(record, EventRecord):
                truncated_desc = self._truncate_description(record.description, available_width, depth)
                node_text = f"[dim]{timestamp_str}[/dim] {truncated_desc}"
                parent_node = depth_nodes.get(depth, tree)
                parent_node.add(Text.from_markup(node_text))
            elif isinstance(record, HistoryRecord):
                record_cost = record.history.get_total_cost_sync()
                if record_cost > 0:
                    cost_str = f"[dim](${record_cost:.2f})[/dim] "
                else:
                    cost_str = ""

                truncated_desc = self._truncate_description(record.description, available_width, depth)

                node_text = f"[dim]{timestamp_str}[/dim] {cost_str}[bold]{truncated_desc}[/bold]"
                parent_node = depth_nodes.get(depth, tree)
                sub_node = parent_node.add(Text.from_markup(node_text))
                # Store this node for potential children
                depth_nodes[depth + 1] = sub_node

    def print_full_history(self, console: Console) -> None:
        """
        Print the complete history to the console without truncation.

        This is intended to be called after the live display closes so that
        users have the full execution history available in their terminal scrollback.

        Args:
            console: The Rich console instance to print to
        """
        if not self.history.records:
            return

        # Build tree with no line limit and wide width for minimal truncation
        tree = self._build_history_tree(max_lines=None, available_width=200)
        console.print(tree)
