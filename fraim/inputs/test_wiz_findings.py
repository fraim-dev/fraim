# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import json
from unittest.mock import Mock, patch
from typing import Dict, Any

from fraim.config.config import Config
from fraim.inputs.wiz_findings import WizFindings, WizFinding


def test_wiz_finding_initialization() -> None:
    """Test WizFinding initialization with sample data."""
    sample_data = {
        "id": "finding-123",
        "targetExternalId": "resource-456",
        "severity": "HIGH",
        "status": "OPEN",
        "result": "FAILED",
        "remediation": "Fix this issue",
        "firstSeenAt": "2024-01-01T00:00:00Z",
        "resource": {
            "id": "res-123",
            "name": "test-resource"
        },
        "rule": {
            "id": "rule-456",
            "name": "test-rule"
        }
    }
    
    finding = WizFinding(sample_data)
    
    assert finding.id == "finding-123"
    assert finding.target_external_id == "resource-456"
    assert finding.severity == "HIGH"
    assert finding.status == "OPEN"
    assert finding.result == "FAILED"
    assert finding.remediation == "Fix this issue"
    assert finding.resource["name"] == "test-resource"
    assert finding.rule["name"] == "test-rule"


def test_wiz_findings_query_variables() -> None:
    """Test that query variables are built correctly."""
    config = Mock(spec=Config)
    
    wiz_input = WizFindings(
        config=config,
        api_token="test-token",
        analyzed_after="2024-01-01T00:00:00Z",
        severity_filter=["HIGH", "CRITICAL"],
        status_filter=["OPEN"]
    )
    
    variables = wiz_input._build_query_variables()
    
    expected = {
        "first": 100,
        "filterBy": {
            "includeDeleted": False,
            "analyzedAt": {"after": "2024-01-01T00:00:00Z"},
            "severity": {"in": ["HIGH", "CRITICAL"]},
            "status": {"in": ["OPEN"]}
        }
    }
    
    assert variables == expected


def test_wiz_findings_query_variables_with_cursor() -> None:
    """Test query variables with pagination cursor."""
    config = Mock(spec=Config)
    
    wiz_input = WizFindings(
        config=config,
        api_token="test-token",
        analyzed_after="2024-01-01T00:00:00Z"
    )
    
    variables = wiz_input._build_query_variables(after_cursor="cursor-123")
    
    assert variables["after"] == "cursor-123"


@patch('fraim.inputs.wiz_findings.requests.post')
def test_wiz_findings_iteration(mock_post: Mock) -> None:
    """Test WizFindings iteration with mocked API responses."""
    config = Mock(spec=Config)
    
    # Mock the first API response with two findings and pagination
    first_response = {
        "data": {
            "configurationFindings": {
                "nodes": [
                    {
                        "id": "finding-1",
                        "severity": "HIGH",
                        "status": "OPEN"
                    },
                    {
                        "id": "finding-2", 
                        "severity": "MEDIUM",
                        "status": "OPEN"
                    }
                ],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor-1"
                }
            }
        }
    }
    
    # Mock the second API response with one finding and no more pages
    second_response = {
        "data": {
            "configurationFindings": {
                "nodes": [
                    {
                        "id": "finding-3",
                        "severity": "LOW", 
                        "status": "RESOLVED"
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": "cursor-2"
                }
            }
        }
    }
    
    # Configure mock to return different responses for each call
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = [first_response, second_response]
    mock_post.return_value = mock_response
    
    wiz_input = WizFindings(
        config=config,
        api_token="test-token",
        analyzed_after="2024-01-01T00:00:00Z"
    )
    
    # Collect all findings from the iterator
    findings = list(wiz_input)
    
    # Verify we got all 3 findings
    assert len(findings) == 3
    assert findings[0].id == "finding-1"
    assert findings[1].id == "finding-2" 
    assert findings[2].id == "finding-3"
    
    # Verify API was called twice for pagination
    assert mock_post.call_count == 2
    
    # Verify the authorization header
    calls = mock_post.call_args_list
    for call in calls:
        headers = call[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


@patch('fraim.inputs.wiz_findings.requests.post')
def test_wiz_findings_graphql_error_handling(mock_post: Mock) -> None:
    """Test error handling for GraphQL errors."""
    config = Mock(spec=Config)
    
    # Mock response with GraphQL errors
    error_response = {
        "errors": [
            {"message": "Authentication failed"}
        ]
    }
    
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = error_response
    mock_post.return_value = mock_response
    
    wiz_input = WizFindings(
        config=config,
        api_token="invalid-token",
        analyzed_after="2024-01-01T00:00:00Z"
    )
    
    # Should raise exception when GraphQL errors are present
    try:
        list(wiz_input)
        assert False, "Expected exception was not raised"
    except Exception as e:
        assert "GraphQL errors" in str(e)
        assert "Authentication failed" in str(e)


if __name__ == "__main__":
    # Simple test runner
    test_wiz_finding_initialization()
    test_wiz_findings_query_variables()
    test_wiz_findings_query_variables_with_cursor()
    test_wiz_findings_iteration()
    test_wiz_findings_graphql_error_handling()
    print("All tests passed!") 