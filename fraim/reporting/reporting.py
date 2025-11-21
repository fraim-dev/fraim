# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Self

logger = logging.getLogger(__name__)


class Reporting:
    """
    Manages output directory for a single workflow run.

    Use as a context manager to ensure proper lifecycle and automatic summary:
        with Reporting.create_run(output_dir, project_name) as reporting:
            reporting.write("file.txt", "content")
            # Summary printed automatically on exit
    """

    @classmethod
    def create_run(
        cls,
        project_name: str,
        auto_print_summary: bool = True,
        output_dir: Path | None = None,
        timestamp: str | None = None,
    ) -> Self:
        """
        Manages a new run directory and return a Reporting instance.

        Args:
            project_name: Name of the project/repository being analyzed
            output_dir: Base directory for all runs (default: current working directory)
            timestamp: Optional timestamp string (default: auto-generated YYYYMMDD_HHMMSS)
            auto_print_summary: If True, print summary on context exit

        Returns:
            Reporting instance configured for this run

        Example:
            >>> with Reporting.create_run("my-project") as reporting:
            ...     reporting.write("results.txt", "analysis complete")
            ...     reporting.write("data.json", json.dumps({"status": "ok"}))
            ...
            Wrote 2 file(s) to: ./my-project_20241121_143020
              • results.txt
              • data.json
        """
        if output_dir is None:
            output_dir = Path.cwd()

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize project name for use in directory name
        safe_project_name = "".join(c if c.isalnum() or c in "_" else "_" for c in project_name).strip("_")
        run_dir = output_dir / f"{safe_project_name}_{timestamp}"

        instance = cls(run_dir, auto_print_summary=auto_print_summary)
        return instance

    def __init__(self, run_dir: Path, auto_print_summary: bool = True):
        """
        Initialize with a run directory path.

        Args:
            run_dir: Path to the run directory (will be created on context entry)
            auto_print_summary: If True, print summary on context exit
        """
        self.run_dir = run_dir
        self._written_files: dict[str, Path] = {}  # filename -> full_path
        self._auto_print_summary = auto_print_summary

    def __enter__(self) -> Self:
        """Enter context - create the run directory."""
        logger.info(f"Creating directory for run reports: {self.run_dir}")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Exit context - print summary if requested."""
        if self._auto_print_summary:
            self.print_summary()

    def write(self, filename: str, content: str) -> Path:
        """
        Write arbitrary content to a file in the run directory.

        Args:
            filename: Name of the file (must not contain path separators)
            content: String content to write

        Returns:
            Full path to the written file

        Raises:
            ValueError: If filename contains path separators
        """
        # Disallow path separators in filename (check both / and \ for cross-platform safety)
        if "/" in filename or "\\" in filename:
            raise ValueError(f"Filename cannot contain path separators: {filename}")

        filepath = self.run_dir / filename

        filepath.write_text(content, encoding="utf-8")

        self._written_files[filename] = filepath
        logger.debug(f"Wrote {filename}")
        return filepath

    def get_path(self, filename: str) -> Path:
        """
        Get the full path for a filename in the run directory.

        Args:
            filename: Name of the file

        Returns:
            Full path (file may not exist yet)
        """
        return self.run_dir / filename

    def get_written_files(self) -> dict[str, Path]:
        """
        Get all files written by this reporting instance.

        Returns:
            Dictionary mapping filename -> full path
        """
        return self._written_files.copy()

    def print_summary(self) -> None:
        """Print a summary of all files written during this run."""
        if not self._written_files:
            print("No files written.")
            return

        print(f"\nWrote {len(self._written_files)} file(s) to: {self.run_dir}")
        for filename in self._written_files.keys():
            print(f"  • {filename}")
