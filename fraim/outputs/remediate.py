# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Remediation output models for describing various types of remediation actions.
Used for generating actionable remediation steps from security findings.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class RemediationType(str, Enum):
    """Types of remediation actions."""
    CODE = "code"
    CLI = "cli"
    CONFIGURATION = "configuration"
    MANUAL = "manual"


class RemediationSeverity(str, Enum):
    """Severity levels for remediation actions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RemediationStatus(str, Enum):
    """Status of a remediation action."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CodeRemediation(BaseSchema):
    """Remediation action for code changes."""
    
    type: Literal[RemediationType.CODE] = RemediationType.CODE
    file_path: str = Field(description="Path to the file that needs to be modified")
    original_code: str = Field(description="The original code that needs to be changed")
    remediated_code: str = Field(description="The corrected/remediated code")
    line_start: int = Field(description="Starting line number for the code change")
    line_end: int = Field(description="Ending line number for the code change")
    description: str = Field(description="Human-readable description of the code change")
    backup_recommended: bool = Field(default=True, description="Whether a backup is recommended before applying")


class CLIRemediation(BaseSchema):
    """Remediation action for CLI commands."""
    
    type: Literal[RemediationType.CLI] = RemediationType.CLI
    command: str = Field(description="The CLI command to execute")
    working_directory: Optional[str] = Field(default=None, description="Working directory to execute the command in")
    description: str = Field(description="Human-readable description of what the command does")
    requires_sudo: bool = Field(default=False, description="Whether the command requires sudo/admin privileges")
    timeout_seconds: Optional[int] = Field(default=None, description="Maximum time to wait for command completion")
    expected_output: Optional[str] = Field(default=None, description="Expected output or success indicator")


class ConfigurationRemediation(BaseSchema):
    """Remediation action for configuration file changes."""
    
    type: Literal[RemediationType.CONFIGURATION] = RemediationType.CONFIGURATION
    config_file: str = Field(description="Path to the configuration file")
    config_path: str = Field(description="JSON path, YAML key, or configuration key to modify")
    original_value: Any = Field(description="The current/original value")
    remediated_value: Any = Field(description="The corrected/remediated value")
    description: str = Field(description="Human-readable description of the configuration change")
    config_format: str = Field(default="json", description="Format of the configuration file (json, yaml, ini, etc.)")
    backup_recommended: bool = Field(default=True, description="Whether a backup is recommended before applying")


class ManualRemediation(BaseSchema):
    """Remediation action for manual steps."""
    
    type: Literal[RemediationType.MANUAL] = RemediationType.MANUAL
    steps: List[str] = Field(description="Ordered list of manual steps to perform")
    description: str = Field(description="Human-readable description of the manual remediation")
    documentation_url: Optional[str] = Field(default=None, description="URL to relevant documentation")
    estimated_time_minutes: Optional[int] = Field(default=None, description="Estimated time to complete in minutes")
    prerequisites: Optional[List[str]] = Field(default=None, description="Prerequisites before performing the steps")


# Union type for all remediation actions
RemediationAction = Union[CodeRemediation, CLIRemediation, ConfigurationRemediation, ManualRemediation]


class RemediationMetadata(BaseSchema):
    """Metadata about the remediation."""
    
    finding_id: Optional[str] = Field(default=None, description="ID of the original finding this remediation addresses")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp when remediation was created")
    created_by: Optional[str] = Field(default=None, description="Tool or person who created the remediation")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence that this remediation will fix the issue (0.0-1.0)")
    risk_level: RemediationSeverity = Field(default=RemediationSeverity.MEDIUM, description="Risk level of the change")


class Remediation(BaseSchema):
    """A complete remediation with action and metadata."""
    
    id: str = Field(description="Unique identifier for this remediation")
    title: str = Field(description="Short title describing the remediation")
    description: str = Field(description="Detailed description of what this remediation accomplishes")
    action: RemediationAction = Field(description="The specific remediation action to perform")
    metadata: RemediationMetadata = Field(description="Metadata about the remediation")
    status: RemediationStatus = Field(default=RemediationStatus.PENDING, description="Current status of the remediation")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorizing the remediation")
    dependencies: Optional[List[str]] = Field(default=None, description="IDs of other remediations that must be completed first")


class RemediationReport(BaseSchema):
    """A report containing multiple remediations."""
    
    version: str = Field(default="1.0.0", description="Version of the remediation report format")
    generated_at: str = Field(description="ISO timestamp when the report was generated")
    generated_by: str = Field(description="Tool or system that generated the report")
    remediations: List[Remediation] = Field(description="List of remediations in this report")
    summary: Optional[Dict[str, Any]] = Field(default=None, description="Summary statistics about the remediations")


def create_code_remediation(
    file_path: str,
    original_code: str,
    remediated_code: str,
    line_start: int,
    line_end: int,
    description: str,
    **kwargs: Any
) -> CodeRemediation:
    """Helper function to create a code remediation."""
    return CodeRemediation(
        file_path=file_path,
        original_code=original_code,
        remediated_code=remediated_code,
        line_start=line_start,
        line_end=line_end,
        description=description,
        **kwargs
    )


def create_cli_remediation(
    command: str,
    description: str,
    **kwargs: Any
) -> CLIRemediation:
    """Helper function to create a CLI remediation."""
    return CLIRemediation(
        command=command,
        description=description,
        **kwargs
    )


def create_config_remediation(
    config_file: str,
    config_path: str,
    original_value: Any,
    remediated_value: Any,
    description: str,
    **kwargs: Any
) -> ConfigurationRemediation:
    """Helper function to create a configuration remediation."""
    return ConfigurationRemediation(
        config_file=config_file,
        config_path=config_path,
        original_value=original_value,
        remediated_value=remediated_value,
        description=description,
        **kwargs
    )


def create_manual_remediation(
    steps: List[str],
    description: str,
    **kwargs: Any
) -> ManualRemediation:
    """Helper function to create a manual remediation."""
    return ManualRemediation(
        steps=steps,
        description=description,
        **kwargs
    )


def create_remediation_report(
    remediations: List[Remediation],
    generated_by: str = "fraim",
    **kwargs: Any
) -> RemediationReport:
    """Helper function to create a complete remediation report."""
    from datetime import datetime
    
    return RemediationReport(
        generated_at=datetime.utcnow().isoformat() + "Z",
        generated_by=generated_by,
        remediations=remediations,
        **kwargs
    ) 