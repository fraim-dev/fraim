# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Component Filtering

Post-processing filters to remove over-granular and misclassified infrastructure components.
Applies intelligent filtering rules to improve infrastructure discovery quality.
"""

import logging
import re
from typing import List

from .types import InfrastructureComponent


def filter_iam_components(components: List[InfrastructureComponent]) -> List[InfrastructureComponent]:
    """
    Filter out IAM-related components that should be treated as security configuration
    rather than infrastructure components.

    Args:
        components: List of infrastructure components

    Returns:
        Filtered list with IAM components removed
    """
    logger = logging.getLogger(__name__)

    iam_service_names = {
        "iam role",
        "iam policy",
        "iam instance profile",
        "iam role policy attachment",
        "iam user",
        "iam group",
        "iam access key",
        "iam policy attachment",
    }

    iam_name_patterns = [
        r"\biam\b",
        r"role(?:_|-)?policy(?:_|-)?attachment",
        r"instance(?:_|-)?profile",
        r"policy(?:_|-)?attachment",
        r"assume(?:_|-)?role(?:_|-)?policy",
    ]

    filtered = []
    removed_count = 0

    for component in components:
        is_iam = False

        # Check service name
        if component.service_name.lower() in iam_service_names:
            is_iam = True

        # Check name patterns
        if not is_iam:
            for pattern in iam_name_patterns:
                if re.search(pattern, component.name.lower()):
                    is_iam = True
                    break

        # Check configuration content
        if not is_iam:
            config_lower = component.configuration.lower()
            iam_config_indicators = [
                "iam role",
                "iam policy",
                "assume role policy",
                "managed policies",
                "policy document",
                "principal",
                "assumerolepolicy",
            ]
            iam_count = sum(1 for indicator in iam_config_indicators if indicator in config_lower)
            if iam_count >= 2:  # Multiple IAM indicators suggest IAM component
                is_iam = True

        if not is_iam:
            filtered.append(component)
        else:
            removed_count += 1
            logger.debug(f"Filtered out IAM component: {component.name}")

    if removed_count > 0:
        logger.info(f"Filtered out {removed_count} IAM components")

    return filtered


def filter_aws_accounts(components: List[InfrastructureComponent]) -> List[InfrastructureComponent]:
    """
    Filter out AWS account entries that represent organizational structure
    rather than infrastructure components.

    Args:
        components: List of infrastructure components

    Returns:
        Filtered list with AWS account components removed
    """
    logger = logging.getLogger(__name__)

    filtered = []
    removed_count = 0

    for component in components:
        is_aws_account = (
            component.service_name.lower() in ["aws account", "cloud account"]
            or "aws account" in component.name.lower()
            or (component.service_name == "AWS Account" and "account" in component.configuration.lower())
        )

        if not is_aws_account:
            filtered.append(component)
        else:
            removed_count += 1
            logger.debug(f"Filtered out AWS account: {component.name}")

    if removed_count > 0:
        logger.info(f"Filtered out {removed_count} AWS account components")

    return filtered


def filter_granular_lambda_components(components: List[InfrastructureComponent]) -> List[InfrastructureComponent]:
    """
    Filter out granular Lambda-related components (permissions, log subscriptions)
    that should be grouped with their parent Lambda function.

    Args:
        components: List of infrastructure components

    Returns:
        Filtered list with granular Lambda components removed
    """
    logger = logging.getLogger(__name__)

    lambda_granular_patterns = [
        r"lambda(?:_|-)?permission",
        r"lambda(?:_|-)?allow(?:_|-)?cloudwatch",
        r"cloudwatch(?:_|-)?log(?:_|-)?subscription",
        r"datadog(?:_|-)?log(?:_|-)?subscription",
        r"log(?:_|-)?subscription(?:_|-)?filter",
    ]

    lambda_service_names = {
        "lambda permission",
        "aws lambda permission",
        "cloudwatch log subscription filter",
        "lambda invoke permission",
    }

    filtered = []
    removed_count = 0

    for component in components:
        is_granular_lambda = False

        # Check service name
        if component.service_name.lower() in lambda_service_names:
            is_granular_lambda = True

        # Check name patterns
        if not is_granular_lambda:
            for pattern in lambda_granular_patterns:
                if re.search(pattern, component.name.lower()):
                    is_granular_lambda = True
                    break

        if not is_granular_lambda:
            filtered.append(component)
        else:
            removed_count += 1
            logger.debug(f"Filtered out granular Lambda component: {component.name}")

    if removed_count > 0:
        logger.info(f"Filtered out {removed_count} granular Lambda components")

    return filtered


def fix_component_types(components: List[InfrastructureComponent]) -> List[InfrastructureComponent]:
    """
    Fix misclassified component types based on service names and configurations.

    Args:
        components: List of infrastructure components

    Returns:
        List with corrected component types
    """
    logger = logging.getLogger(__name__)

    corrections = 0

    for component in components:
        original_type = component.type

        # Redis/ElastiCache should be cache, not other
        if component.type == "other" and (
            "redis" in component.service_name.lower()
            or "elasticache" in component.service_name.lower()
            or "redis" in component.name.lower()
        ):
            component.type = "cache"

        # Security groups should be network_security
        elif component.type == "other" and (
            "security group" in component.service_name.lower()
            or "sg" in component.name.lower()
            and "security" in component.configuration.lower()
        ):
            component.type = "network_security"

        # Lambda functions should be serverless_function
        elif component.type == "other" and (
            "lambda function" in component.service_name.lower() or "aws lambda" in component.service_name.lower()
        ):
            component.type = "serverless_function"

        # Route53 zones should be dns
        elif component.type == "other" and (
            "route53" in component.service_name.lower() or "dns" in component.service_name.lower()
        ):
            component.type = "dns"

        # CloudWatch should be monitoring
        elif component.type == "other" and (
            "cloudwatch" in component.service_name.lower()
            or "datadog" in component.service_name.lower()
            or "monitoring" in component.name.lower()
        ):
            component.type = "monitoring"

        if component.type != original_type:
            corrections += 1
            logger.debug(f"Corrected type for {component.name}: {original_type} -> {component.type}")

    if corrections > 0:
        logger.info(f"Corrected {corrections} component type classifications")

    return components


def apply_infrastructure_filters(components: List[InfrastructureComponent]) -> List[InfrastructureComponent]:
    """
    Apply all infrastructure component filters to improve discovery quality.

    Args:
        components: List of raw infrastructure components

    Returns:
        Filtered and corrected list of infrastructure components
    """
    logger = logging.getLogger(__name__)

    original_count = len(components)
    logger.info(f"Applying infrastructure filters to {original_count} components")

    # Apply filters in sequence
    components = filter_iam_components(components)
    components = filter_aws_accounts(components)
    components = filter_granular_lambda_components(components)
    components = fix_component_types(components)

    final_count = len(components)
    filtered_count = original_count - final_count

    logger.info(
        f"Infrastructure filtering complete: {original_count} -> {final_count} components ({filtered_count} filtered)"
    )

    return components
