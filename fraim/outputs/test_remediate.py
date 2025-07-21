# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Tests for the Remediate output models.
Demonstrates usage patterns for different remediation types.
"""

import json
from datetime import datetime
from typing import Dict, Any

from fraim.outputs.remediate import (
    RemediationType,
    RemediationSeverity,
    RemediationStatus,
    CodeRemediation,
    CLIRemediation,
    ConfigurationRemediation,
    ManualRemediation,
    RemediationMetadata,
    Remediation,
    RemediationReport,
    create_code_remediation,
    create_cli_remediation,
    create_config_remediation,
    create_manual_remediation,
    create_remediation_report,
)


def test_code_remediation() -> None:
    """Test creating and serializing a code remediation."""
    code_fix = create_code_remediation(
        file_path="src/auth.py",
        original_code="password = request.args.get('password')",
        remediated_code="password = request.form.get('password')",
        line_start=45,
        line_end=45,
        description="Fix password parameter extraction from query string to form data for security",
        backup_recommended=True
    )
    
    assert code_fix.type == RemediationType.CODE
    assert code_fix.file_path == "src/auth.py"
    assert code_fix.line_start == 45
    assert code_fix.backup_recommended is True
    
    # Test serialization
    json_data = code_fix.model_dump()
    assert json_data["type"] == "code"
    assert "filePath" in json_data  # Check camelCase conversion


def test_cli_remediation() -> None:
    """Test creating and serializing a CLI remediation."""
    cli_fix = create_cli_remediation(
        command="npm audit fix --force",
        description="Update vulnerable npm packages to latest secure versions",
        working_directory="/path/to/project",
        requires_sudo=False,
        timeout_seconds=300,
        expected_output="found 0 vulnerabilities"
    )
    
    assert cli_fix.type == RemediationType.CLI
    assert cli_fix.command == "npm audit fix --force"
    assert cli_fix.requires_sudo is False
    assert cli_fix.timeout_seconds == 300


def test_configuration_remediation() -> None:
    """Test creating and serializing a configuration remediation."""
    config_fix = create_config_remediation(
        config_file="app.json",
        config_path="security.allowInsecureConnections",
        original_value=True,
        remediated_value=False,
        description="Disable insecure connections in application configuration",
        config_format="json",
        backup_recommended=True
    )
    
    assert config_fix.type == RemediationType.CONFIGURATION
    assert config_fix.config_file == "app.json"
    assert config_fix.original_value is True
    assert config_fix.remediated_value is False


def test_manual_remediation() -> None:
    """Test creating and serializing a manual remediation."""
    manual_fix = create_manual_remediation(
        steps=[
            "1. Navigate to AWS IAM console",
            "2. Select the affected user account",
            "3. Go to Security credentials tab",
            "4. Rotate the access keys",
            "5. Update application configuration with new keys"
        ],
        description="Rotate compromised AWS access keys",
        documentation_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
        estimated_time_minutes=15,
        prerequisites=["AWS admin access", "Application deployment capability"]
    )
    
    assert manual_fix.type == RemediationType.MANUAL
    assert len(manual_fix.steps) == 5
    assert manual_fix.estimated_time_minutes == 15
    assert manual_fix.prerequisites is not None


def test_complete_remediation() -> None:
    """Test creating a complete remediation with metadata."""
    code_action = create_code_remediation(
        file_path="src/sql.py",
        original_code="query = f\"SELECT * FROM users WHERE id = {user_id}\"",
        remediated_code="query = \"SELECT * FROM users WHERE id = %s\"\ncursor.execute(query, (user_id,))",
        line_start=23,
        line_end=23,
        description="Fix SQL injection vulnerability by using parameterized queries"
    )
    
    metadata = RemediationMetadata(
        finding_id="wiz-finding-123",
        created_at=datetime.utcnow().isoformat() + "Z",
        created_by="fraim-security-scanner",
        confidence_score=0.95,
        risk_level=RemediationSeverity.HIGH
    )
    
    remediation = Remediation(
        id="rem-001",
        title="Fix SQL Injection in User Query",
        description="Replace string formatting with parameterized query to prevent SQL injection",
        action=code_action,
        metadata=metadata,
        status=RemediationStatus.PENDING,
        tags=["sql-injection", "security", "database"],
        dependencies=None
    )
    
    assert remediation.id == "rem-001"
    assert remediation.action.type == RemediationType.CODE
    assert remediation.metadata.confidence_score == 0.95
    assert remediation.tags is not None and "sql-injection" in remediation.tags


def test_remediation_report() -> None:
    """Test creating a complete remediation report."""
    # Create multiple remediations
    code_rem = Remediation(
        id="rem-001",
        title="Fix SQL Injection",
        description="Fix SQL injection vulnerability",
        action=create_code_remediation(
            file_path="src/db.py",
            original_code="old code",
            remediated_code="new code",
            line_start=1,
            line_end=1,
            description="Fix SQL injection"
        ),
        metadata=RemediationMetadata(),
        status=RemediationStatus.PENDING
    )
    
    cli_rem = Remediation(
        id="rem-002",
        title="Update Dependencies",
        description="Update vulnerable npm packages",
        action=create_cli_remediation(
            command="npm audit fix",
            description="Fix npm vulnerabilities"
        ),
        metadata=RemediationMetadata(),
        status=RemediationStatus.PENDING
    )
    
    report = create_remediation_report(
        remediations=[code_rem, cli_rem],
        generated_by="fraim-test",
        summary={
            "total_remediations": 2,
            "by_type": {
                "code": 1,
                "cli": 1
            },
            "by_severity": {
                "high": 1,
                "medium": 1
            }
        }
    )
    
    assert len(report.remediations) == 2
    assert report.generated_by == "fraim-test"
    assert report.summary is not None and report.summary["total_remediations"] == 2
    assert report.version == "1.0.0"


def test_json_serialization() -> None:
    """Test that all remediation types can be serialized to JSON."""
    remediations = [
        create_code_remediation(
            file_path="test.py",
            original_code="bad code",
            remediated_code="good code",
            line_start=1,
            line_end=1,
            description="Test fix"
        ),
        create_cli_remediation(
            command="test command",
            description="Test CLI"
        ),
        create_config_remediation(
            config_file="config.json",
            config_path="test.value",
            original_value="old",
            remediated_value="new",
            description="Test config"
        ),
        create_manual_remediation(
            steps=["Step 1", "Step 2"],
            description="Test manual"
        )
    ]
    
    for action in remediations:
        # Test that each can be serialized to JSON
        json_str = action.model_dump_json()
        parsed = json.loads(json_str)
        
        # Verify type field exists and is correct
        assert "type" in parsed
        assert parsed["type"] in ["code", "cli", "configuration", "manual"]
        
        # Verify description exists
        assert "description" in parsed


def test_enum_values() -> None:
    """Test that enum values are correct."""
    assert RemediationType.CODE == "code"
    assert RemediationType.CLI == "cli"
    assert RemediationType.CONFIGURATION == "configuration"
    assert RemediationType.MANUAL == "manual"
    
    assert RemediationSeverity.CRITICAL == "critical"
    assert RemediationSeverity.HIGH == "high"
    assert RemediationSeverity.MEDIUM == "medium"
    assert RemediationSeverity.LOW == "low"
    assert RemediationSeverity.INFO == "info"
    
    assert RemediationStatus.PENDING == "pending"
    assert RemediationStatus.IN_PROGRESS == "in_progress"
    assert RemediationStatus.COMPLETED == "completed"
    assert RemediationStatus.FAILED == "failed"
    assert RemediationStatus.SKIPPED == "skipped"


if __name__ == "__main__":
    # Simple test runner
    test_code_remediation()
    test_cli_remediation()
    test_configuration_remediation()
    test_manual_remediation()
    test_complete_remediation()
    test_remediation_report()
    test_json_serialization()
    test_enum_values()
    print("All remediation tests passed!") 