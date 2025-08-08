# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utility for writing JSON workflow output files.

This module provides a function to write workflow analysis results in JSON format with
timestamped filenames. It is used by analysis workflows to persist their findings.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fraim.config import Config


def write_json_output(
    results: Dict[str, Any],
    workflow_name: str,
    config: Config,
    custom_filename: Optional[str] = None,
    include_timestamp: bool = True,
    output_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Write workflow results to a JSON file with optional timestamping.

    Args:
        results: The workflow results to write as JSON
        workflow_name: Name of the workflow (used in filename if custom_filename not provided)
        config: Configuration object containing output_dir and project_path
        custom_filename: Optional custom filename (overrides default pattern)
        include_timestamp: Whether to include timestamp in filename (default: True)
        output_dir: Optional output directory (overrides config.output_dir if provided)

    Returns:
        Path to the written file if successful, None if output_dir not configured

    Raises:
        Exception: Re-raises any exception that occurs during file writing
    """
    # Use provided output_dir or fall back to config
    target_output_dir = output_dir or getattr(config, "output_dir", None)

    if not target_output_dir:
        return None

    try:
        # Create output directory if it doesn't exist
        os.makedirs(target_output_dir, exist_ok=True)

        # Generate filename
        if custom_filename:
            output_filename = custom_filename
        else:
            # Extract app name from project path
            app_name = getattr(config, "project_path", "application")
            app_name = os.path.basename(app_name.rstrip(os.sep)) or "application"

            if include_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"{workflow_name}_{app_name}_{timestamp}.json"
            else:
                output_filename = f"{workflow_name}_{app_name}.json"

        output_path = os.path.join(target_output_dir, output_filename)

        # Write JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        config.logger.info(f"{workflow_name.replace('_', ' ').title()} results written to {output_path}")
        return output_path

    except Exception as write_exc:
        config.logger.error(f"Failed to write {workflow_name} results: {write_exc}")
        raise
