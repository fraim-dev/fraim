# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from __future__ import annotations

import fnmatch
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .basepath import BasePathFS


def list_dir(
    fs: BasePathFS,
    target_path: str | Path = ".",
    *,
    ignore_globs: Iterable[str] = [],
    show_hidden: bool = False,
    max_entries: int = 1_000,
) -> str:
    """Return a recursive directory listing with proper nesting and fair truncation.

    Uses hierarchical BFS to ensure siblings are shown before children, while balancing
    exploration fairly among directory subtrees through round-robin processing.

    Args:
        fs: BasePathFS instance to use for path resolution
        target_path: Path to the directory to list
        ignore_globs: List of glob patterns to ignore
        show_hidden: Whether to show hidden files
        max_entries: Maximum number of entries to return

    Returns:
        String with one line per entry, using '-' prefix, '/' suffix for dirs, and indentation for hierarchy.
        Children are nested directly under their parents. Siblings get equal priority before going deeper.
    """
    p = fs.resolve(target_path, must_exist=True)
    if not p.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {p}")

    # Build accepted entries tree using dual-tree BFS algorithm
    accepted_entries = _traverse_path(p, ignore_globs, show_hidden, max_entries)

    # Serialize accepted entries tree in depth-first order
    lines = []
    for e in accepted_entries:
        lines.append(_serialize_entry(fs, e))
    return "\n".join(lines)


type Entry = FileEntry | DirEntry | TruncationEntry
"""
Simple tree structure for entries that will be displayed in the list_dir output.

Represents a node that can be either a file, directory, or hidden entry,
allowing for flexible representation of filesystem hierarchies.
"""


@dataclass
class DirEntry:
    """A node in the Entry tree representing a directory. It may contain have child entries."""

    name: str
    children: list[Entry]


@dataclass
class FileEntry:
    """A leaf node in the Entry tree representing a file."""

    name: str


@dataclass
class TruncationEntry:
    """A leaf node in the Entry tree representing multiple entries that have been truncated."""

    count: int  # number of truncated entries
    path: Path  # path to the directory that contains the truncated entries


root_dir_entry = DirEntry(name="..", children=[])


def _serialize_entry(fs: BasePathFS, root: Entry, depth: int = 0, indent: str = "  ", prefix: str = "- ") -> str:
    """Serialize an Entry tree to output lines in depth-first order."""
    lines = []

    stack = [(root, depth)]
    while stack:
        node, depth = stack.pop()

        match node:
            case FileEntry():
                lines.append(f"{indent * depth}{prefix}{node.name}")
            case DirEntry():
                lines.append(f"{indent * depth}{prefix}{node.name}/")
                for child in reversed(node.children):
                    stack.append((child, depth + 1))
            case TruncationEntry():
                # Get path relative to the base path
                path_rel = fs.relative_to_root(node.path)
                lines.append(
                    f"{indent * depth}... {node.count} more entries not shown. Use 'list_dir {path_rel}' to see more."
                )

    return "\n".join(lines)


def _create_entry(path: Path, parent: DirEntry | None) -> Entry:
    """Create an Entry from a path."""

    if parent is None:
        parent = root_dir_entry

    if path.is_dir():
        entry: Entry = DirEntry(name=path.name, children=[])

    else:
        entry = FileEntry(name=path.name)

    if parent:
        parent.children.append(entry)

    return entry


def _create_truncation_entry(count: int, path: Path, parent: DirEntry) -> TruncationEntry:
    """Create a TruncationEntry from a count and path."""
    entry = TruncationEntry(count=count, path=path)

    if parent:
        parent.children.append(entry)

    return entry


@dataclass
class TraversalNode:
    """Represents a directory or file entry in the hierarchical BFS traversal."""

    name: str
    path: Path

    parent: TraversalNode

    visited: bool

    entry: DirEntry | None

    queue: deque[TraversalNode]

    @staticmethod
    def from_path(path: Path, *, parent: TraversalNode, entry: DirEntry | None = None) -> TraversalNode:
        """Create a TraversalNode from a path."""
        return TraversalNode(name=path.name, path=path, parent=parent, entry=entry, visited=False, queue=deque([]))

    def visit(self, entry: Entry, children: list[Path]) -> None:
        """Record that a node was visited, setting its entry and children."""
        self.entry = entry if isinstance(entry, DirEntry) else None
        self.queue = deque([TraversalNode.from_path(path, parent=self) for path in children])
        self.visited = True


class RootTraversalNode(TraversalNode):
    """Represents the root of the traversal tree."""

    def __init__(self) -> None:
        super().__init__(name="", path=Path(".."), parent=self, entry=None, visited=False, queue=deque([]))


def _traverse_path(root_path: Path, ignore_globs: Iterable[str], show_hidden: bool, max_entries: int) -> list[Entry]:
    """Traverse the root path to build an Entry tree"""

    # This function uses a variant of a breadth-first traversal of the root path to build an Entry tree
    # with the following propertries
    #
    # 1. The number of (dir or file) entries in the tree is limited to max_entries
    #
    # When the tree must be truncated due to max_entries:
    #
    # 2. All siblings at one level are included in the entry tree before any children are added
    # 3. The tree is balanced. The same number of descendants are shown for each sibling.
    # 4. A TruncationEntry is added for each node with remaining children.
    #
    # Why go to all this work???
    #
    # Because we want `list_dir foo` to give the LLM a good understanding of the file
    # layout, while still fitting in the output of a single tool call.
    #
    # The LLM can pass a more-specific path to get details further down the tree, so it's ok to truncate
    # entries there. It's not ok to truncate siblings (at least the root), because there's no other way
    # to see them. Balancing the visits across subtrees ensures that the LLM gets a good understanding
    # of the entire file layout, not just details about one subtree.
    #
    # How do we do this???
    #
    # The breadth-first traversal builds this Entry tree efficiently, visiting only the directory and
    # file entries that will be shown in the output. This avoids traversing parts of the filesystem
    # that are too big to include in the output.
    #
    # The traversal uses a queue for each Node (aka directory) to fairly allocate entries across siblings.
    # On each iteration, we find the next unvisited decendant of the current node and add it to the
    # Entry tree. This ensures properties 2 and 3 are met.
    #
    # As an optimization, once a node has no more unvisited descendants, we remove it from its parent's
    # queue. Similarly, if a node has only child, we'll promote that child directly to the parent's queue.

    # Root of the Entry tree that will be returned
    entry_count = -1  # root entry doesn't count, because it won't be displayed in the output.

    # First node for the BFS traversal of the filesystem
    root_node = TraversalNode.from_path(root_path, parent=RootTraversalNode(), entry=None)

    # Breadth-first-ish traversal of the filesystem to build the Entry tree:
    #   1. Visit all siblings before any children
    #   2. Balance the visits across subtrees (at the same level) by
    #      round-robin processing of descendants.
    start: TraversalNode | None = root_node
    while entry_count < max_entries and start:
        # Find the next unvisited node
        node = start
        while node.visited:
            node = node.queue.popleft()

        # and visit it
        entry = _create_entry(node.path, node.parent.entry if node.parent else None)
        entry_count += 1
        node.visit(entry=entry, children=_get_dir_entries(node.path, ignore_globs, show_hidden))

        # then reinsert the lineage
        while node != start:
            parent = node.parent
            match len(node.queue):
                case 0:
                    # no more descendants, so don't reinsert
                    pass
                case 1:
                    # Optimizatiom: only child, so add it directly to our parent's queue
                    only_child = node.queue.popleft()
                    parent.queue.append(only_child)
                case _:
                    # Multiple descendants
                    parent.queue.append(node)
            node = parent

        match len(start.queue):
            case 0:
                # We're done!
                start = None
            case 1:
                # Optimizatiom: only one child, so make it the start
                start = start.queue.popleft()

    # Add TruncationEntry nodes for any nodes with remaining children
    stack = [root_node]
    while stack:
        node = stack.pop()

        # If there are unvisited children, add a TruncationEntry
        unvisited_count = len([True for c in node.queue if not c.visited])
        if unvisited_count > 0 and node.entry and isinstance(node.entry, DirEntry):
            _create_truncation_entry(unvisited_count, node.path, node.entry)

        # Traverse the visited children
        stack.extend([c for c in node.queue if c.visited])

    return root_node.entry.children if root_node.entry else []


def _get_dir_entries(dir_path: Path, ignore_globs: Iterable[str], show_hidden: bool) -> list[Path]:
    """Get filtered and sorted entries for a directory."""
    if not dir_path.is_dir():
        return []

    try:
        entries = []
        for entry in dir_path.iterdir():
            if not _should_ignore_entry(entry, ignore_globs, show_hidden):
                entries.append(entry)

        # Sort entries: directories first, then alphabetically
        entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
        return entries

    except PermissionError:
        # Return empty list for directories we can't read
        return []


def _should_ignore_entry(entry: Path, ignore_globs: Iterable[str], show_hidden: bool) -> bool:
    """Check if an entry should be ignored based on filters."""
    # Always ignore symlinks for security
    if entry.is_symlink():
        return True

    if not show_hidden and entry.name.startswith("."):
        return True

    # Check ignore patterns
    for ignore_glob in ignore_globs:
        if fnmatch.fnmatch(entry.name, ignore_glob):
            return True

    return False
