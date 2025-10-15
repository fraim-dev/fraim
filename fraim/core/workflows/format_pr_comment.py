# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Format PR comment for risks.
"""

from typing import Any

from jinja2 import Template

PR_COMMENT_TEMPLATE = """
{%- if not risks_by_type %}
No risks were identified in this PR.
{%- else %}
# Security Risk Review Required

The following security risks have been identified and require review:

{%- for risk_type, type_risks in risks_by_type.items() %}

## {{ risk_type }}
{%- for risk in type_risks %}

### {{ risk.message.text }} (Severity: {{ risk.properties.risk_severity }})

**Location**: `{{ risk.locations[0].physicalLocation.artifactLocation.uri }}:{{ risk.locations[0].physicalLocation.region.startLine }}`

**Explanation**:
{%- for explanation in risk.properties.explanation.split('. ') %}
{%- if explanation.strip() %}
* {{ explanation.strip() }}
{%- endif %}
{%- endfor %}

---
{%- endfor %}
{%- endfor %}

Please review these risks and ensure appropriate mitigations are in place before approving.
{%- endif %}
"""


def format_pr_comment(risks: list[Any]) -> str:
    """Format a list of risks into a PR comment using a Jinja template.

    Args:
        risks: List of SARIF Result objects with risk overlay properties

    Returns:
        A formatted string suitable for a PR comment
    """
    # Group risks by risk type for better organization
    risks_by_type: dict[str, list[Any]] = {}
    for risk in risks:
        risk_type = risk.properties.risk_type
        if risk_type not in risks_by_type:
            risks_by_type[risk_type] = []
        risks_by_type[risk_type].append(risk)

    # Render the Jinja template
    template = Template(PR_COMMENT_TEMPLATE)

    return template.render(risks_by_type=risks_by_type).strip()
