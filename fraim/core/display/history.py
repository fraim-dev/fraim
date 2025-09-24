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

        # Reserve space for panel borders (2 lines)
        max_lines = console_height - 2

        # Flatten all records to determine total count and get most recent ones
        all_records = self._flatten_records(self.history.records)

        # If we have more records than can fit, truncate to show most recent
        # Each record consumes at least one line, so limit the records we try to render
        truncated = len(all_records) > max_lines
        if truncated:
            # Take the most recent records that fit
            recent_records = all_records[-max_lines:]
        else:
            recent_records = all_records

        tree = Tree(self.title, style="bold blue")

        # Calculate available width for truncation
        # Account for panel padding (4 chars), timestamp (10 chars), and some buffer
        console_width = options.max_width or console.size.width
        available_width = console_width - 20  # Conservative buffer for padding and formatting

        # Add the recent records to tree
        self._add_flattened_records_to_tree(recent_records, tree, available_width)

        yield Panel(tree, title="Execution History", border_style="blue", padding=(1, 2))

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
                truncated_desc = self._truncate_description(record.description, available_width, depth)
                node_text = f"[dim]{timestamp_str}[/dim] [bold]{truncated_desc}[/bold]"
                parent_node = depth_nodes.get(depth, tree)
                sub_node = parent_node.add(Text.from_markup(node_text))
                # Store this node for potential children
                depth_nodes[depth + 1] = sub_node
