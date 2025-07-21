# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import json
import requests  # type: ignore
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Union, cast
from typing_extensions import Annotated

from fraim.config.config import Config


class WizResource:
    """A Wiz resource object."""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.provider_id = data.get("providerId")
        self.name = data.get("name")
        self.native_type = data.get("nativeType")
        self.type = data.get("type")
        self.region = data.get("region")
        self.subscription = self._create_subscription(data.get("subscription", {}))
        
    def _create_subscription(self, data: Dict[str, Any]) -> Optional[Any]:
        """Create a simple object for subscription data."""
        if not data:
            return None
        subscription = type('Subscription', (), {})()
        subscription.id = data.get("id")
        subscription.name = data.get("name")
        subscription.external_id = data.get("externalId")
        subscription.cloud_provider = data.get("cloudProvider")
        return subscription


class WizRule:
    """A Wiz rule object."""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.short_id = data.get("shortId")
        self.graph_id = data.get("graphId")
        self.name = data.get("name")
        self.description = data.get("description")
        self.remediation_instructions = data.get("remediationInstructions")
        self.function_as_control = data.get("functionAsControl")
        self.builtin = data.get("builtin")
        self.target_native_types = data.get("targetNativeTypes", [])
        self.supports_nrt = data.get("supportsNRT")
        self.subject_entity_type = data.get("subjectEntityType")
        self.service_type = data.get("serviceType")


@dataclass
class WizFinding:
    """A single Wiz configuration finding."""
    
    # The raw data from the API - this will be the only required init parameter
    raw_data: Dict[str, Any]
    
    # All other fields will be populated in __post_init__
    id: Optional[str] = field(default=None, init=False)
    target_external_id: Optional[str] = field(default=None, init=False)
    severity: Optional[str] = field(default=None, init=False)
    status: Optional[str] = field(default=None, init=False)
    result: Optional[str] = field(default=None, init=False)
    remediation: Optional[str] = field(default=None, init=False)
    first_seen_at: Optional[str] = field(default=None, init=False)
    resource: Optional[WizResource] = field(default=None, init=False)
    rule: Optional[WizRule] = field(default=None, init=False)
    security_sub_categories: List[Dict[str, Any]] = field(default_factory=list, init=False)
    ignore_rules: List[Dict[str, Any]] = field(default_factory=list, init=False)
    
    def __post_init__(self) -> None:
        """Initialize the finding fields from the raw API data."""
        data = self.raw_data
        
        self.id = data.get("id")
        self.target_external_id = data.get("targetExternalId")
        self.severity = data.get("severity")
        self.status = data.get("status")
        self.result = data.get("result")
        self.remediation = data.get("remediation")
        self.first_seen_at = data.get("firstSeenAt")
        
        # Create proper objects for nested data
        resource_data = data.get("resource", {})
        self.resource = WizResource(resource_data) if resource_data else None
        
        rule_data = data.get("rule", {})
        self.rule = WizRule(rule_data) if rule_data else None
        
        self.security_sub_categories = data.get("securitySubCategories", [])
        self.ignore_rules = data.get("ignoreRules", [])


@dataclass
class WizFindings:
    """Input for collecting Wiz configuration findings via GraphQL API."""
    
    config: Config
    api_token: Annotated[str, {"help": "Wiz API token for authentication"}]
    endpoint: Annotated[str, {"help": "Wiz GraphQL API endpoint"}] = "https://api.us17.app.wiz.io/graphql"
    
    # Pagination and filtering options
    first: Annotated[int, {"help": "Number of findings to fetch per page"}] = 10
    include_deleted: Annotated[bool, {"help": "Whether to include deleted findings"}] = False
    analyzed_after: Annotated[Optional[str], {"help": "ISO timestamp - only include findings analyzed after this date"}] = None
    
    # Additional filter options
    severity_filter: Annotated[Optional[List[str]], {"help": "Filter by severity levels"}] = field(default_factory=list)
    status_filter: Annotated[Optional[List[str]], {"help": "Filter by status"}] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Set default analyzed_after if not provided."""
        if self.analyzed_after is None:
            # Default to findings from the last 24 hours
            from datetime import datetime, timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            self.analyzed_after = yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def _build_query_variables(self, after_cursor: Optional[str] = None) -> Dict[str, Any]:
        """Build GraphQL query variables."""
        filter_by = {
            "includeDeleted": self.include_deleted,
            "analyzedAt": {
                "after": self.analyzed_after
            }
        }
        
        # Add severity filter if specified
        if self.severity_filter:
            filter_by["severity"] = {"in": self.severity_filter}
            
        # Add status filter if specified  
        if self.status_filter:
            filter_by["status"] = {"in": self.status_filter}
        
        variables = {
            "first": self.first,
            "filterBy": filter_by
        }
        
        if after_cursor:
            variables["after"] = after_cursor
            
        return variables
    
    def _make_graphql_request(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Make a GraphQL request to the Wiz API."""
        query = """
        query CloudConfigurationFindingsPage(
            $filterBy: ConfigurationFindingFilters
            $first: Int
            $after: String
            $orderBy: ConfigurationFindingOrder
        ) {
            configurationFindings(
                filterBy: $filterBy
                first: $first
                after: $after
                orderBy: $orderBy
            ) {
                nodes {
                    id
                    targetExternalId
                    deleted
                    targetObjectProviderUniqueId
                    firstSeenAt
                    severity
                    result
                    status
                    remediation
                    resource {
                        id
                        providerId
                        name
                        nativeType
                        type
                        region
                        subscription {
                            id
                            name
                            externalId
                            cloudProvider
                        }
                        projects {
                            id
                            name
                            riskProfile {
                                businessImpact
                            }
                        }
                        tags {
                            key
                            value
                        }
                    }
                    rule {
                        id
                        shortId
                        graphId
                        name
                        description
                        remediationInstructions
                        functionAsControl
                        builtin
                        targetNativeTypes
                        supportsNRT
                        subjectEntityType
                        serviceType
                    }
                    securitySubCategories {
                        id
                        title
                        category {
                            id
                            name
                            framework {
                                id
                                name
                            }
                        }
                    }
                    ignoreRules{
                        id
                        name
                        enabled
                        expiredAt
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """
        
        payload = {
            "query": query,
            "variables": variables
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        
        return cast(Dict[str, Any], response.json())
    
    def __iter__(self) -> Iterator[WizFinding]:
        """Iterate through all Wiz configuration findings with pagination."""
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            variables = self._build_query_variables(after_cursor)
            response_data = self._make_graphql_request(variables)
            
            # Handle GraphQL errors
            if "errors" in response_data:
                raise Exception(f"GraphQL errors: {response_data['errors']}")
                
            # Extract data
            findings_data = response_data.get("data", {}).get("configurationFindings", {})
            nodes = findings_data.get("nodes", [])
            page_info = findings_data.get("pageInfo", {})
                        
            # Yield each finding
            for node in nodes:
                yield WizFinding(node)
            
            # Check if there are more pages
            # has_next_page = page_info.get("hasNextPage", False)
            has_next_page = False
            after_cursor = page_info.get("endCursor") 