# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code workflow-specific SARIF model extensions.
These models extend the base SARIF models with additional triage and analysis fields.
"""

from enum import Enum

from pydantic import Field

from fraim.outputs.sarif import BaseSchema


class ResultCategoryEnum(str, Enum):
    """Category classification of security findings."""

    MISUNDERSTANDING = "misunderstanding"
    """The finding is based on a misunderstanding of the code's behavior or context."""

    VULNERABILITY = "vulnerability"
    """A security vulnerability that could be exploited to compromise the system."""

    HYGIENE = "hygiene"
    """Code quality or security hygiene issue that doesn't directly lead to exploitation."""

    MISCONFIGURATION = "misconfiguration"
    """A configuration issue that could lead to security problems."""

    DEPENDENCY_RISK = "dependency_risk"
    """A risk introduced by third-party dependencies or libraries."""


class AttackComplexityEnum(str, Enum):
    """Complexity level required to exploit a vulnerability."""

    LOW = "low"
    """Exploitation requires minimal skill or resources."""

    MEDIUM = "medium"
    """Exploitation requires moderate skill or specific conditions."""

    HIGH = "high"
    """Exploitation requires advanced skill, specific conditions, or significant resources."""


class ResultProperties(BaseSchema):
    category: ResultCategoryEnum = Field(description="Category classification of the finding")
    impact_assessment: str = Field(description="Assessment of potential impact of the vulnerability")
    attack_complexity: AttackComplexityEnum = Field(description="Complexity required to exploit the vulnerability")
    attack_vectors: list[str] = Field(description="List of potential attack vectors for exploiting the vulnerability")
    remediation: str = Field(description="Recommended steps to remediate the vulnerability")
