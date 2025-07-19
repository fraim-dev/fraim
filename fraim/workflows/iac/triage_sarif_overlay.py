# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code workflow-specific SARIF model extensions.
These models extend the base SARIF models with additional triage and analysis fields.
"""

from typing import List

from pydantic import Field

from fraim.outputs.sarif import BaseSchema


class ResultProperties(BaseSchema):
    # Enhanced triage fields for code workflow
    impact_assessment: str = Field(description="Assessment of potential impact of the vulnerability")
    attack_complexity: str = Field(description="Complexity required to exploit the vulnerability (Low/Medium/High)")
    attack_vectors: List[str] = Field(description="List of potential attack vectors for exploiting the vulnerability")
    remediation: str = Field(description="Recommended steps to remediate the vulnerability")
