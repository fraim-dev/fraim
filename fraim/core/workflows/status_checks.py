# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
from dataclasses import dataclass
from typing import Annotated

logger = logging.getLogger(__name__)


@dataclass
class StatusCheckOptions:
    status_check: Annotated[bool, {"help": "Whether to interpret file input as Github status check output as JSON"}] = (
        False
    )
