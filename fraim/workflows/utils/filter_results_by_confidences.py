# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for filtering results by confidence.
"""

from typing import List

from fraim.outputs import risk, sarif


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]


def filter_risks_by_confidence(results: List[risk.Risk], confidence_threshold: int) -> List[risk.Risk]:
    """Filter results by confidence."""
    return [result for result in results if result.confidence > confidence_threshold]
