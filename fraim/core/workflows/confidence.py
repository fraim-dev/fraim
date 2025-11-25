# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
"""
Functions for working with SARIF results.
"""

import logging
from dataclasses import dataclass
from typing import Annotated

from fraim.outputs import sarif

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFilterOptions:
    confidence: Annotated[
        int,
        {
            "help": "Minimum confidence threshold (1-10) for filtering findings (default: 7)",
            "choices": range(1, 11),  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        },
    ] = 7


"""
TODO: Organization nits:

"confidence" isn't actually a SARIF thing (its a custom property that we added). I'd put this in file fraim/core/workflows/mixins/confidence.py.

write_sarif_and_html_report isn't workflow specific. Consider moving it to a fraim/core/ouputs/sarif.py or something like that.
"""


def filter_results_by_confidence(results: list[sarif.Result], confidence_threshold: int) -> list[sarif.Result]:
    return [result for result in results if result.properties.confidence > confidence_threshold]
