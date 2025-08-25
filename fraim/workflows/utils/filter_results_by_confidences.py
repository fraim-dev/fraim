# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Utilities for filtering results by confidence.
"""

from typing import List, TypeVar

from fraim.outputs import sarif

# Generic type for objects with confidence field
T = TypeVar('T')


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter SARIF results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]


def filter_by_confidence_float(items: List[T], confidence_threshold: float) -> List[T]:
    """
    Filter items by confidence where confidence is a float field (0.0-1.0).
    
    Args:
        items: List of items with a 'confidence' attribute
        confidence_threshold: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Filtered list of items with confidence >= threshold
    """
    return [item for item in items if hasattr(item, 'confidence') and item.confidence >= confidence_threshold]


def convert_int_confidence_to_float(confidence_int: int) -> float:
    """
    Convert integer confidence (1-10) to float confidence (0.0-1.0).
    
    Args:
        confidence_int: Integer confidence value (1-10)
        
    Returns:
        Float confidence value (0.0-1.0)
    """
    return confidence_int / 10.0
