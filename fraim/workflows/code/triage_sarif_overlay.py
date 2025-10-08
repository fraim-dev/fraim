# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code workflow-specific SARIF model extensions.
These models extend the base SARIF models with additional triage and analysis fields.
"""

from typing import Literal
from pydantic import Field

from fraim.outputs.sarif import BaseSchema


class ResultProperties(BaseSchema):
    # Enhanced triage fields for code workflow
    impact_assessment: str = Field(description="Assessment of potential impact of the vulnerability")
    attack_complexity: str = Field(description="Complexity required to exploit the vulnerability (Low/Medium/High)")
    attack_vectors: list[str] = Field(description="List of potential attack vectors for exploiting the vulnerability")
    remediation: str = Field(description="Recommended steps to remediate the vulnerability")
    risk_type: str = Field(
        description="The category of risk identified (e.g., 'Database Changes', 'Public Facing VMs'). Must match one of the risks specified in the workflow configuration."
    )
    risk_severity: Literal["critical", "high", "medium", "low"] = Field(
        description="The assessed impact level of the risk. Based on potential security impact and exposure surface area."
    )
    explanation: str = Field(
        description="Detailed technical explanation of why this code change introduces risk. Should include: 1) What specific change triggered the risk flag, 2) How it relates to the risk type, 3) What security implications need investigation."
    )
