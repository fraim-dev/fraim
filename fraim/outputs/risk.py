# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Pydantic models for risks.
Used for generating standardized risks.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class Risk(BaseSchema):
    """Represents a flagged risk."""

    risk: str = Field(description="The risk that was flagged.")
    explanation: str = Field(description="The explanation of the risk.")
    file_path: str = Field(description="The path to the file that contains the risk.")
    line_number: int = Field(description="The line number of the risk.")
    column_number: int = Field(description="The column number of the risk.")
    risk_type: str = Field(description="The type of risk.")
    risk_severity: str = Field(description="The severity of the risk.")
    confidence: int = Field(
        description="Confidence that the result is a true risk from 1 (least confident) to 10 (most confident)"
    )
