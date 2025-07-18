# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for filtering results by confidence.
"""

from typing import List

from fraim.outputs import sarif


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]
