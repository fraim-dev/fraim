# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Risk Flagger workflow-specific SARIF model extensions.
These models extend the base SARIF models with additional fields.
"""

from typing import Literal

from pydantic import Field

from fraim.outputs.sarif import BaseSchema


class ResultProperties(BaseSchema):
    # Enhanced fields for risk flagger workflow
    risk_type: str = Field(
        description="The category of risk identified (e.g., 'Database Changes', 'Public Facing VMs'). Must match one of the risks specified in the workflow configuration."
    )
    risk_severity: Literal["critical", "high", "medium", "low"] = Field(
        description="The assessed impact level of the risk. Based on potential security impact and exposure surface area."
    )
    explanation: str = Field(
        description="Detailed technical explanation of why this code change introduces risk. Should include: 1) What specific change triggered the risk flag, 2) How it relates to the risk type, 3) What security implications need investigation."
    )
    confidence: int = Field(
        ge=1,
        le=10,
        description="Confidence that the result is a true risk from 1 (least confident) to 10 (most confident). Higher confidence (8-10) requires clear evidence in code changes. Lower confidence (1-4) indicates more context needed. Where more context is needed, use the tools available to you to gather that context.",
    )
