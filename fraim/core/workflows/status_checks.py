# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
"""
Utility for writing SARIF and HTML security scan reports.

This module provides a function to write scan results in both SARIF (JSON) and HTML formats.
It is used by workflows to persist and present vulnerability findings after analysis.
"""

import logging
from dataclasses import dataclass
from typing import Annotated

logger = logging.getLogger(__name__)


@dataclass
class StatusCheckOptions:
    status_check: Annotated[bool, {"help": "Whether to interpret file input as Github status check output as JSON"}] = (
        False
    )
